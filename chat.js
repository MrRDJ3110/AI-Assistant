import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const MAX_MESSAGE_LENGTH = 2_000;
const MAX_MESSAGES = 8;

function setCorsHeaders(request, response) {
  const origin = request.headers.origin;
  const allowedOrigin = process.env.ALLOWED_ORIGIN;
  if (origin && allowedOrigin && origin === allowedOrigin) {
    response.setHeader("Access-Control-Allow-Origin", origin);
    response.setHeader("Vary", "Origin");
  }
}

export default async function handler(request, response) {
  setCorsHeaders(request, response);

  if (request.method === "OPTIONS") {
    response.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
    response.setHeader("Access-Control-Allow-Headers", "Content-Type");
    return response.status(204).end();
  }
  if (request.method !== "POST") return response.status(405).json({ error:"Method not allowed." });

  const origin = request.headers.origin;
  if (origin && process.env.ALLOWED_ORIGIN && origin !== process.env.ALLOWED_ORIGIN) {
    return response.status(403).json({ error:"This website is not allowed to use the AI endpoint." });
  }
  if (!process.env.OPENAI_API_KEY) {
    return response.status(500).json({ error:"The server is missing OPENAI_API_KEY." });
  }

  const rawMessages = Array.isArray(request.body?.messages) ? request.body.messages : [];
  const messages = rawMessages
    .slice(-MAX_MESSAGES)
    .filter(message => message && (message.role === "user" || message.role === "assistant") && typeof message.content === "string")
    .map(message => ({ role:message.role, content:message.content.trim().slice(0, MAX_MESSAGE_LENGTH) }))
    .filter(message => message.content);

  if (!messages.length) return response.status(400).json({ error:"Send at least one message." });

  const transcript = messages
    .map(message => (message.role === "assistant" ? "EVERYTHING AI" : "User") + ": " + message.content)
    .join("\n");

  try {
    const completion = await client.responses.create({
      model: process.env.OPENAI_MODEL || "gpt-6-luna",
      instructions:"You are EVERYTHING AI, a concise, friendly web assistant. Answer in plain text. Do not claim to control devices, open apps, browse the web, or complete actions you cannot actually perform. If a request could be unsafe, explain the limitation briefly and offer a safe alternative.",
      input:transcript
    });
    const reply = completion.output_text?.trim();
    if (!reply) throw new Error("The model returned no text.");
    return response.status(200).json({ reply });
  } catch (error) {
    console.error("OpenAI request failed:", error);
    return response.status(502).json({ error:"The AI service could not answer right now. Please try again." });
  }
}
