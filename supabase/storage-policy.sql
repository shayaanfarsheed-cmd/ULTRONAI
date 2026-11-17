CREATE POLICY ultron_checkpoint_owner_read
ON storage.objects
FOR SELECT
TO authenticated
USING (
    bucket_id = 'checkpoints'
    AND (storage.foldername(name))[1] = (SELECT auth.uid())::text
);
