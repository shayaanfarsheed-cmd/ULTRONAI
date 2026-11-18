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


-- Private owner-only data library. Objects use the path <owner-auth-uuid>/<file-name>.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM storage.buckets WHERE id = 'data-library') THEN
    INSERT INTO storage.buckets (id, name, public, file_size_limit)
    VALUES ('data-library', 'data-library', false, 20971520);
  ELSE
    UPDATE storage.buckets SET name = 'data-library', public = false, file_size_limit = 20971520
    WHERE id = 'data-library';
  END IF;
END
$$;

DROP POLICY IF EXISTS ultron_data_library_owner_select ON storage.objects;
CREATE POLICY ultron_data_library_owner_select ON storage.objects
FOR SELECT TO authenticated
USING (bucket_id = 'data-library' AND (storage.foldername(name))[1] = (SELECT auth.uid())::text);

DROP POLICY IF EXISTS ultron_data_library_owner_insert ON storage.objects;
CREATE POLICY ultron_data_library_owner_insert ON storage.objects
FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'data-library' AND (storage.foldername(name))[1] = (SELECT auth.uid())::text);

DROP POLICY IF EXISTS ultron_data_library_owner_update ON storage.objects;
CREATE POLICY ultron_data_library_owner_update ON storage.objects
FOR UPDATE TO authenticated
USING (bucket_id = 'data-library' AND (storage.foldername(name))[1] = (SELECT auth.uid())::text)
WITH CHECK (bucket_id = 'data-library' AND (storage.foldername(name))[1] = (SELECT auth.uid())::text);

DROP POLICY IF EXISTS ultron_data_library_owner_delete ON storage.objects;
CREATE POLICY ultron_data_library_owner_delete ON storage.objects
FOR DELETE TO authenticated
USING (bucket_id = 'data-library' AND (storage.foldername(name))[1] = (SELECT auth.uid())::text);
