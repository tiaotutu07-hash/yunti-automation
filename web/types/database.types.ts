export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      problems: {
        Row: {
          id: string
          raw_latex: string
          source: string | null
          year: number | null
          district: string | null
          exam_type: string | null
          reviewed_by_wife: boolean
          reviewed_by_chief: boolean
          primary_tag: string | null
          method_tags: string[] | null
          difficulty: number | null
          novelty: string | null
          typical_errors: string[] | null
          brief_analysis: string | null
          tagged_by: string | null
          tagged_at: string | null
          wife_notes: string | null
          created_at: string
        }
        Insert: {
          id?: string
          raw_latex: string
          source?: string | null
          year?: number | null
          district?: string | null
          exam_type?: string | null
          reviewed_by_wife?: boolean
          reviewed_by_chief?: boolean
          primary_tag?: string | null
          method_tags?: string[] | null
          difficulty?: number | null
          novelty?: string | null
          typical_errors?: string[] | null
          brief_analysis?: string | null
          tagged_by?: string | null
          tagged_at?: string | null
          wife_notes?: string | null
          created_at?: string
        }
        Update: {
          id?: string
          raw_latex?: string
          source?: string | null
          year?: number | null
          district?: string | null
          exam_type?: string | null
          reviewed_by_wife?: boolean
          reviewed_by_chief?: boolean
          primary_tag?: string | null
          method_tags?: string[] | null
          difficulty?: number | null
          novelty?: string | null
          typical_errors?: string[] | null
          brief_analysis?: string | null
          tagged_by?: string | null
          tagged_at?: string | null
          wife_notes?: string | null
          created_at?: string
        }
      }
    }
  }
}

export type Problem = Database['public']['Tables']['problems']['Row']
