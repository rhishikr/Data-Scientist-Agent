-- Allow the anon key to upload/download/delete files in the
-- pipeline-artifacts Storage bucket.
-- Run this in the Supabase SQL Editor after 002_disable_rls.sql.

-- Ensure the bucket exists and is marked public
INSERT INTO storage.buckets (id, name, public)
VALUES ('pipeline-artifacts', 'pipeline-artifacts', true)
ON CONFLICT (id) DO UPDATE SET public = true;

-- Allow anyone to SELECT (download) objects in this bucket
CREATE POLICY "Allow public read on pipeline-artifacts"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'pipeline-artifacts');

-- Allow anyone to INSERT (upload) objects in this bucket
CREATE POLICY "Allow public insert on pipeline-artifacts"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'pipeline-artifacts');

-- Allow anyone to UPDATE objects in this bucket
CREATE POLICY "Allow public update on pipeline-artifacts"
  ON storage.objects FOR UPDATE
  USING (bucket_id = 'pipeline-artifacts');

-- Allow anyone to DELETE objects in this bucket
CREATE POLICY "Allow public delete on pipeline-artifacts"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'pipeline-artifacts');
