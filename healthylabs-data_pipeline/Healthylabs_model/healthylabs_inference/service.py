"""High-level query service wiring safety, retrieval, reflection, and synthesis."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from typing import cast

from healthylabs_inference.api.request_models import QueryRequest, QueryResponse
from healthylabs_inference.core.config import Settings, get_settings
from healthylabs_inference.core.database_clients import (
    MinioImageClient,
    Neo4jSearchClient,
    PostgresCitationClient,
)
from healthylabs_inference.core.embeddings import BioLORDEmbedder, CLIPTextEmbedder
from healthylabs_inference.core.llm_client import GeminiClient
from healthylabs_inference.orchestrator.intent_guard import IntentGuard, emergency_response
from healthylabs_inference.orchestrator.memory import SessionMemoryManager, SessionMemoryUpdate
from healthylabs_inference.orchestrator.reflection import ReflectionDecision, ReflectionEngine
from healthylabs_inference.orchestrator.self_rag_router import (
    RoutingDecision,
    SelfRAGRouter,
    Strategy,
)
from healthylabs_inference.retrieval.kg_overrides import KnowledgeGraphOverrides
from healthylabs_inference.retrieval.models import RetrievalBundle
from healthylabs_inference.retrieval.neo4j_search import Neo4jVectorRetriever
from healthylabs_inference.retrieval.reranker import dedupe_and_rerank
from healthylabs_inference.retrieval.strategies.decompose import DecompositionRetrievalStrategy
from healthylabs_inference.retrieval.strategies.direct import DirectRetrievalStrategy
from healthylabs_inference.retrieval.strategies.hyde import HyDERetrievalStrategy
from healthylabs_inference.retrieval.strategies.multi_query import MultiQueryRetrievalStrategy
from healthylabs_inference.retrieval.strategies.visual import VisualRetrievalStrategy
from healthylabs_inference.synthesis.conflict_resolver import ConflictResolver
from healthylabs_inference.synthesis.response_builder import ResponseBuilder

logger = logging.getLogger("HealthyLabs.Inference")


@dataclass(slots=True)
class QueryService:
    settings: Settings
    llm_client: GeminiClient
    intent_guard: IntentGuard
    router: SelfRAGRouter
    reflection: ReflectionEngine
    direct_strategy: DirectRetrievalStrategy
    hyde_strategy: HyDERetrievalStrategy
    multi_query_strategy: MultiQueryRetrievalStrategy
    decompose_strategy: DecompositionRetrievalStrategy
    kg_overrides: KnowledgeGraphOverrides
    conflict_resolver: ConflictResolver
    response_builder: ResponseBuilder
    memory_manager: SessionMemoryManager
    visual_strategy: VisualRetrievalStrategy

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> QueryService:
        resolved = settings or get_settings()
        llm = GeminiClient(resolved)
        neo4j_client = Neo4jSearchClient(resolved)
        pg_client = PostgresCitationClient(resolved)
        retriever = Neo4jVectorRetriever(BioLORDEmbedder(resolved), neo4j_client)
        visual_strategy = VisualRetrievalStrategy(
            clip_embedder=CLIPTextEmbedder(),
            neo4j_client=neo4j_client,
            minio_client=MinioImageClient(resolved),
            settings=resolved,
        )
        return cls(
            settings=resolved,
            llm_client=llm,
            intent_guard=IntentGuard(llm),
            router=SelfRAGRouter(resolved, llm),
            reflection=ReflectionEngine(llm),
            direct_strategy=DirectRetrievalStrategy(retriever),
            hyde_strategy=HyDERetrievalStrategy(retriever, llm),
            multi_query_strategy=MultiQueryRetrievalStrategy(retriever),
            decompose_strategy=DecompositionRetrievalStrategy(retriever),
            kg_overrides=KnowledgeGraphOverrides(neo4j_client),
            conflict_resolver=ConflictResolver(),
            response_builder=ResponseBuilder(llm, pg_client, resolved),
            memory_manager=SessionMemoryManager(resolved, llm),
            visual_strategy=visual_strategy,
        )

    def close(self) -> None:
        self.response_builder.citation_client.close()
        self.direct_strategy.retriever.search_client.close()

    def answer(self, request: QueryRequest) -> QueryResponse:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.answer_async(request))
        raise RuntimeError("Use answer_async() from within an async context.")

    async def answer_async(self, request: QueryRequest) -> QueryResponse:
        try:
            return await asyncio.wait_for(
                self._run_pipeline(request),
                timeout=self.settings.request_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:  # noqa: UP041
            raise RuntimeError(
                f"Query exceeded {self.settings.request_timeout_seconds}s timeout"
            ) from exc

    async def _run_pipeline(self, request: QueryRequest) -> QueryResponse:
        logger.info(
            "Query received | session=%s query_len=%d history_turns=%d",
            request.session_id,
            len(request.query_text),
            len(request.chat_history),
        )
        intent = self.intent_guard.classify(request.query_text)
        logger.info("Intent classified | intent=%s source=%s", intent.intent, intent.source)
        if intent.intent == "emergency":
            return QueryResponse(
                answer=emergency_response(
                    query_text=request.query_text,
                    patient_context=request.patient_context,
                    location_context=request.request_metadata.get("location_context", {}),
                ),
                strategy_used="emergency",
                contradictions_found=False,
                confidence_score=1.0,
                safety_flags=["emergency_intent"],
                escalation_required=True,
                updated_session_summary=request.session_summary,
                updated_pinned_medical_facts=request.pinned_medical_facts,
                updated_open_questions=request.open_questions,
                updated_safety_notes=request.safety_notes,
                retrieval_trace=[{"stage": "intent_guard", "decision": asdict(intent)}],
            )

        decision = self.router.route(request)
        logger.info(
            "Strategy selected | strategy=%s source=%s kg_required=%s",
            decision.strategy,
            decision.source,
            decision.knowledge_graph_override_required,
        )
        bundle, visual_results = await asyncio.gather(
            self._retrieve_async(request, decision),
            self._retrieve_visual_async(request.query_text),
        )
        bundle.chunks = dedupe_and_rerank(bundle.chunks, max_items=self.settings.max_pool_size)
        logger.info(
            "Retrieval complete | chunks=%d visuals=%d confidence=%.3f",
            len(bundle.chunks),
            len(visual_results),
            bundle.confidence,
        )

        reflection = self.reflection.assess(
            query_text=request.query_text,
            strategy=decision.strategy,
            bundle=bundle,
            threshold=decision.confidence_threshold,
        )
        reflection = await self._run_reflection_retries(request, decision, bundle, reflection)

        kg_facts = self.kg_overrides.collect(request) if decision.knowledge_graph_override_required else []
        conflict_report = self.conflict_resolver.analyze(bundle.chunks)
        safety_flags = list(conflict_report.notes)
        if kg_facts:
            safety_flags.append("patient_specific_kg_facts_found")
            bundle.trace.append(
                {"stage": "kg_overrides", "facts_found": len(kg_facts), "facts": kg_facts[:5]}
            )
        if bundle.confidence < decision.confidence_threshold:
            safety_flags.append("low_retrieval_confidence")

        built = self.response_builder.build(
            request=request,
            chunks=bundle.chunks,
            contradictions_found=conflict_report.contradictions_found,
            safety_flags=safety_flags,
            patient_specific_kg_facts=kg_facts,
            visual_results=visual_results,
        )
        escalation_required = (bundle.confidence < 0.45) or conflict_report.contradictions_found
        logger.info(
            "Response built | citations=%d contradictions=%s escalation=%s",
            len(built.citations),
            conflict_report.contradictions_found,
            escalation_required,
        )
        memory_update = await self._update_memory(request, built.answer, safety_flags)
        return QueryResponse(
            answer=built.answer,
            strategy_used=decision.strategy,
            contradictions_found=conflict_report.contradictions_found,
            citations=built.citations,
            visual_assets=built.visual_assets,
            confidence_score=round(bundle.confidence, 3),
            safety_flags=safety_flags,
            escalation_required=escalation_required,
            updated_session_summary=memory_update.session_summary,
            updated_pinned_medical_facts=memory_update.pinned_medical_facts,
            updated_open_questions=memory_update.open_questions,
            updated_safety_notes=memory_update.safety_notes,
            retrieval_trace=[
                {"stage": "intent_guard", "decision": asdict(intent)},
                {"stage": "router", "decision": asdict(decision)},
                {"stage": "reflection", "decision": asdict(reflection)},
                *bundle.trace,
            ],
        )

    async def _run_reflection_retries(
        self,
        request: QueryRequest,
        original_decision: RoutingDecision,
        bundle: RetrievalBundle,
        reflection: ReflectionDecision,
    ) -> ReflectionDecision:
        remaining = self.settings.max_reflection_loops
        current_reflection = reflection
        while not current_reflection.sufficient and remaining > 0:
            remaining -= 1
            retry_strategy = _retry_strategy(current_reflection.recommended_strategy)
            retry_decision = RoutingDecision(
                strategy=retry_strategy,
                reason=f"Reflection retry: {current_reflection.reason}",
                sub_queries=[request.query_text],
                confidence_threshold=original_decision.confidence_threshold,
                source="reflection",
            )
            retry_bundle = await self._retrieve_async(request, retry_decision)
            bundle.chunks = dedupe_and_rerank(
                bundle.chunks + retry_bundle.chunks,
                max_items=self.settings.max_pool_size,
            )
            bundle.trace.extend(retry_bundle.trace)
            current_reflection = self.reflection.assess(
                query_text=request.query_text,
                strategy=retry_decision.strategy,
                bundle=bundle,
                threshold=original_decision.confidence_threshold,
            )
        return current_reflection

    def _retrieve(self, request: QueryRequest, decision: RoutingDecision) -> RetrievalBundle:
        if decision.strategy == "hyde":
            return self.hyde_strategy.run(request.query_text, request.patient_context)
        if decision.strategy == "multi_query":
            return self.multi_query_strategy.run(request.query_text, decision.sub_queries)
        if decision.strategy == "decompose":
            return self.decompose_strategy.run(request.query_text, decision.sub_queries)
        return self.direct_strategy.run(request.query_text)

    async def _retrieve_async(self, request: QueryRequest, decision: RoutingDecision) -> RetrievalBundle:
        if decision.strategy == "decompose":
            return await self.decompose_strategy.arun(request.query_text, decision.sub_queries)
        return await asyncio.to_thread(self._retrieve, request, decision)

    async def _retrieve_visual_async(self, query_text: str):
        if not self.settings.enable_visual_retrieval:
            return []
        try:
            return await asyncio.to_thread(self.visual_strategy.run, query_text)
        except Exception as exc:
            logger.warning("Visual retrieval failed: %s", exc)
            return []

    async def _update_memory(
        self,
        request: QueryRequest,
        answer: str,
        safety_flags: list[str],
    ) -> SessionMemoryUpdate:
        update = await asyncio.to_thread(
            self.memory_manager.update,
            request=request,
            answer=answer,
            safety_flags=safety_flags,
        )
        logger.info(
            "Session memory updated | session=%s source=%s summary_present=%s pinned_keys=%d",
            request.session_id,
            update.source,
            bool(update.session_summary),
            len(update.pinned_medical_facts),
        )
        return update


def _retry_strategy(candidate: str) -> Strategy:
    if candidate in {"hyde", "decompose"}:
        return cast(Strategy, candidate)
    return "multi_query"
