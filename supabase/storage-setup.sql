DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM storage.buckets WHERE id = 'checkpoints') THEN
    INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
    VALUES (
      'checkpoints',
      'checkpoints',
      false,
      45000000,
      ARRAY['application/octet-stream', 'application/json']::text[]
    );
  ELSE
    UPDATE storage.buckets
    SET name = 'checkpoints',
        public = false,
        file_size_limit = 45000000,
        allowed_mime_types = ARRAY['application/octet-stream', 'application/json']::text[]
    WHERE id = 'checkpoints';
  END IF;
END
$$;

DROP POLICY IF EXISTS ultron_checkpoint_owner_read ON storage.objects;
CREATE POLICY ultron_checkpoint_owner_read
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'checkpoints'
  AND (storage.foldername(name))[1] = (SELECT auth.uid())::text
);
