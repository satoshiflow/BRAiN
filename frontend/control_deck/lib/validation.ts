import { z } from "zod";

/**
 * Validation schemas for BRAiN Control Deck
 *
 * Security Note:
 * - Always validate user input on both client and server
 * - Size limits prevent DoS attacks
 * - Type validation prevents injection attacks
 */

// Mission schemas
export const MissionCreateSchema = z.object({
  name: z.string()
    .min(3, "Name must be at least 3 characters")
    .max(100, "Name too long (max 100 characters)"),

  description: z.string()
    .max(500, "Description too long (max 500 characters)")
    .optional(),

  type: z.enum(["autonomous", "manual", "scheduled"]),

  priority: z.number()
    .int("Priority must be an integer")
    .min(0, "Priority must be at least 0")
    .max(10, "Priority must be at most 10"),

  config: z.record(z.string(), z.unknown()).optional(),
});

export type MissionCreate = z.infer<typeof MissionCreateSchema>;

// Skill execution schemas
export const SkillExecuteSchema = z.object({
  parameters: z.record(
    z.string(),
    z.union([z.string(), z.number(), z.boolean(), z.record(z.string(), z.unknown())])
  ).optional(),

  timeout: z.number()
    .int()
    .min(1000, "Timeout must be at least 1 second")
    .max(300000, "Timeout must be at most 5 minutes")
    .optional(),
});

export type SkillExecute = z.infer<typeof SkillExecuteSchema>;

// Agent schemas
export const AgentConfigSchema = z.object({
  name: z.string()
    .min(2, "Name must be at least 2 characters")
    .max(50, "Name too long"),

  capabilities: z.array(z.string()).optional(),

  max_retries: z.number()
    .int()
    .min(0)
    .max(10)
    .optional(),
});

export type AgentConfig = z.infer<typeof AgentConfigSchema>;

// AXE Identity schemas
export const AXEIdentitySchema = z.object({
  name: z.string()
    .min(2, "Name must be at least 2 characters")
    .max(100, "Name too long"),

  role: z.string()
    .min(2, "Role must be at least 2 characters")
    .max(100, "Role too long"),

  description: z.string()
    .max(500, "Description too long")
    .optional(),

  personality_traits: z.string()
    .max(1000, "Personality traits too long")
    .optional(),
});

export type AXEIdentity = z.infer<typeof AXEIdentitySchema>;

// Knowledge document schemas
export const KnowledgeDocumentSchema = z.object({
  title: z.string()
    .min(3, "Title must be at least 3 characters")
    .max(200, "Title too long"),

  content: z.string()
    .min(10, "Content must be at least 10 characters")
    .max(50000, "Content too long (max 50,000 characters)"),

  tags: z.array(z.string().max(50)).max(20, "Too many tags").optional(),

  category: z.string().max(50).optional(),
});

export type KnowledgeDocument = z.infer<typeof KnowledgeDocumentSchema>;

// Template variable schemas
export const TemplateVariablesSchema = z.record(
  z.string(),
  z.union([
    z.string().max(1000),
    z.number(),
    z.boolean(),
    z.array(z.string()).max(100),
    z.record(z.string(), z.unknown()),
  ])
);

export type TemplateVariables = z.infer<typeof TemplateVariablesSchema>;

/**
 * Helper function to safely validate and parse data
 *
 * @example
 * const result = safeValidate(MissionCreateSchema, formData);
 * if (!result.success) {
 *   // Handle validation errors
 *   console.error(result.errors);
 *   return;
 * }
 * // Use validated data
 * await createMission(result.data);
 */
export function safeValidate<T extends z.ZodType>(
  schema: T,
  data: unknown
): { success: true; data: z.infer<T> } | { success: false; errors: z.ZodError } {
  try {
    const validated = schema.parse(data);
    return { success: true, data: validated };
  } catch (error) {
    if (error instanceof z.ZodError) {
      return { success: false, errors: error };
    }
    throw error;
  }
}

/**
 * Format Zod errors for display to users
 *
 * @example
 * const result = safeValidate(schema, data);
 * if (!result.success) {
 *   const errorMessages = formatZodErrors(result.errors);
 *   setFormErrors(errorMessages);
 * }
 */
export function formatZodErrors(error: z.ZodError): Record<string, string> {
  const formatted: Record<string, string> = {};

  error.issues.forEach((issue) => {
    const path = issue.path.join(".");
    formatted[path] = issue.message;
  });

  return formatted;
}
