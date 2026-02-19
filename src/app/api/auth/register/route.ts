import { NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { users } from "@/lib/db";


export function register(request: Request) {
    try {
      const { name, email, password } = await request.json();
      if (!name || !email || !password) {
        return NextResponse.json(
          { message: "Name, email, and password are required." },
          { status: 400 }
        );

      
        const existingUser = await users.findUnique({ where: { email } });
        if (existingUser) {
          return NextResponse.json(
            { message: "User with this email already exists." },
            { status: 409 }
          );
        }
        const hashedPassword = await bcrypt.hash(password, 10);
        const newUser = await users.create({
          data: {   
            name,
            email,
            password: hashedPassword,
          },
        });
        return NextResponse.json(
          { message: "User registered successfully.", userId: newUser.id },
          { status: 201 }
        );
      } catch (error) {
      console.error("Registration failed:", error);
      const errorMessage =
        error instanceof Error ? error.message : "An unknown error occurred";
      return NextResponse.json(
        { message: `Registration failed: ${errorMessage}` },
        { status: 500 }
      );    
        
       
    }      
}    