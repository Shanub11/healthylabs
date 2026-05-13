import { NextRequest, NextResponse } from 'next/server';

const RAG_API_URL =
  process.env.HEALTHYLABS_RAG_API_URL ||
  'http://127.0.0.1:8005/refinery/v1/chat/diagnostic';

type DiagnosticRequestBody = {
  question?: string;
  session_id?: string;
  chat_history?: {
    role?: 'user' | 'assistant';
    content?: string;
  }[];
  user_profile?: {
    age?: number | null;
    sex?: string | null;
    conditions?: string[];
    allergies?: string[];
    current_medications?: string[];
    habits?: string[];
    family_history?: string[];
    height?: number | null;
    weight?: number | null;
  };
  location_context?: {
    country_code?: string | null;
    timezone?: string | null;
    locale?: string | null;
    latitude?: number | null;
    longitude?: number | null;
    location_permission?: string | null;
  };
};

async function requestBodyFromClient(request: NextRequest): Promise<{
  body: DiagnosticRequestBody;
  image?: File;
}> {
  const contentType = request.headers.get('content-type') || '';
  if (!contentType.includes('multipart/form-data')) {
    return { body: (await request.json()) as DiagnosticRequestBody };
  }

  const formData = await request.formData();
  const payload = formData.get('payload');
  const image = formData.get('image');
  return {
    body: payload ? JSON.parse(String(payload)) as DiagnosticRequestBody : {},
    image: image instanceof File ? image : undefined,
  };
}

async function imageToUploadedPayload(image?: File) {
  if (!image) {
    return [];
  }
  if (!image.type.startsWith('image/')) {
    throw new Error('Only image uploads are supported for chat.');
  }
  const maxBytes = 8 * 1024 * 1024;
  if (image.size > maxBytes) {
    throw new Error('Image must be smaller than 8 MB.');
  }
  const bytes = Buffer.from(await image.arrayBuffer());
  return [
    {
      filename: image.name || 'uploaded-image',
      content_type: image.type || 'image/png',
      data_base64: bytes.toString('base64'),
    },
  ];
}

export async function POST(request: NextRequest) {
  try {
    const { body, image } = await requestBodyFromClient(request);
    const question = body.question?.trim();

    if (!question) {
      return NextResponse.json(
        { message: 'Question is required.' },
        { status: 400 }
      );
    }
    const uploadedImages = await imageToUploadedPayload(image);

    const response = await fetch(RAG_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question,
        session_id: body.session_id ?? null,
        chat_history: (body.chat_history ?? [])
          .filter(message => message.content?.trim())
          .slice(-20)
          .map(message => ({
            role: message.role === 'assistant' ? 'assistant' : 'user',
            content: message.content?.trim(),
          })),
        uploaded_images: uploadedImages,
        user_profile: {
          age: body.user_profile?.age ?? null,
          sex: body.user_profile?.sex ?? null,
          conditions: body.user_profile?.conditions ?? [],
          allergies: body.user_profile?.allergies ?? [],
          current_medications: body.user_profile?.current_medications ?? [],
          habits: body.user_profile?.habits ?? [],
          family_history: body.user_profile?.family_history ?? [],
          height: body.user_profile?.height ?? null,
          weight: body.user_profile?.weight ?? null,
        },
        location_context: {
          country_code: body.location_context?.country_code ?? 'IN',
          timezone: body.location_context?.timezone ?? null,
          locale: body.location_context?.locale ?? null,
          latitude: body.location_context?.latitude ?? null,
          longitude: body.location_context?.longitude ?? null,
          location_permission: body.location_context?.location_permission ?? null,
        },
      }),
    });

    const payload = await response.json().catch(() => null);

    if (!response.ok) {
      return NextResponse.json(
        payload || { message: 'Health assistant request failed.' },
        { status: response.status }
      );
    }

    return NextResponse.json(payload);
  } catch (error) {
    console.error('Diagnostic chat proxy failed:', error);
    const message = error instanceof Error ? error.message : 'Unable to reach the health assistant service.';
    return NextResponse.json(
      { message },
      { status: 502 }
    );
  }
}
