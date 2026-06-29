-- ============================================================
-- Asset Tracker - 월별 자산 목표 추가 테이블 스키마
-- Supabase Dashboard -> SQL Editor 에서 복사하여 실행
-- ============================================================

CREATE TABLE IF NOT EXISTS monthly_goals (
  id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id       UUID NOT NULL,
  year          INT  NOT NULL,
  month         INT  NOT NULL,
  target_amount BIGINT DEFAULT 0,
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, year, month)
);
ALTER TABLE monthly_goals ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "own_goals" ON monthly_goals;
CREATE POLICY "own_goals" ON monthly_goals
  FOR ALL USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
