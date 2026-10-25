import { z } from "zod";

export const resumeCreateSchema = z.object({
  title: z.string().min(1).max(200).default("My Resume"),
  content: z.string().min(20),
  skills: z.array(z.string()).default([]),
});

export const trackerStatusSchema = z.enum([
  "saved",
  "applied",
  "interview",
  "offer",
  "rejected",
]);

export const jobSourceSchema = z.enum(["Himalayas", "Jobicy", "JSearch"]);

export const trackerCreateSchema = z.object({
  job_id: z.string().min(1),
  title: z.string().min(1),
  company: z.string().min(1),
  apply_url: z.string().min(1),
  source: jobSourceSchema,
  status: trackerStatusSchema.default("saved"),
  score: z.number().int().min(0).max(100).nullable().optional(),
  notes: z.string().nullable().optional(),
  cover_letter: z.string().nullable().optional(),
});

export const trackerUpdateSchema = z
  .object({
    status: trackerStatusSchema.optional(),
    notes: z.string().nullable().optional(),
    score: z.number().int().min(0).max(100).nullable().optional(),
    cover_letter: z.string().nullable().optional(),
  })
  .refine((v) => Object.keys(v).length > 0, { message: "At least one field required" });

export const agentRunSchema = z.object({
  resume_id: z.string().optional(),
  resume_text: z.string().optional(),
  query: z.string().min(1).optional(),
  max_jobs: z.number().int().min(1).max(20).optional(),
  location: z.string().nullable().optional(),
  tags: z.array(z.string()).optional(),
});

export const idParamSchema = z.string().uuid().or(z.string().min(1).max(128));
