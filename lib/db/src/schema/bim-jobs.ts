import { pgTable, text, serial, integer, timestamp, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const bimJobsTable = pgTable("bim_jobs", {
  id: text("id").primaryKey(),
  meetingTitle: text("meeting_title"),
  meetingDate: text("meeting_date"),
  meetingNotes: text("meeting_notes").notNull(),
  status: text("status").notNull().default("pending"),
  progress: integer("progress").notNull().default(0),
  currentStep: text("current_step"),
  steps: jsonb("steps"),
  errorMessage: text("error_message"),
  ifcContent: text("ifc_content"),
  fileSize: integer("file_size"),
  extractedElements: jsonb("extracted_elements"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  completedAt: timestamp("completed_at"),
});

export const insertBimJobSchema = createInsertSchema(bimJobsTable).omit({
  createdAt: true,
  completedAt: true,
});

export type InsertBimJob = z.infer<typeof insertBimJobSchema>;
export type BimJob = typeof bimJobsTable.$inferSelect;
