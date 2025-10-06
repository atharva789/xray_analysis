DO $$
DECLARE
  i INT; -- user counter
  j INT; -- dicom counter
  k INT; -- slice counter
  aid_val INT;
  stat_id_val INT;
  dicom_id_val INT;
  file_id_val INT;
BEGIN
  FOR i IN 1..50 LOOP
    -- Insert into ACCOUNTS
    INSERT INTO ACCOUNTS (USERNAME, EMAIL, FNAME, LNAME, PSWRD_HASH, DOB)
    VALUES (
      'user_' || i,
      'user_' || i || '@example.com',
      'First' || i,
      'Last' || i,
      decode(md5(random()::text), 'hex'),
      DATE '1990-01-01' + (i || ' days')::interval
    )
    RETURNING AID INTO aid_val;

    -- Insert into PATIENTS
    INSERT INTO PATIENTS (AID, MRN) VALUES (aid_val, 100000 + i);

    -- For each user: 5 DICOMs
    FOR j IN 1..5 LOOP
      -- Insert patient stat
      INSERT INTO PATIENT_STATS (AGASTON_SCORE)
      VALUES (floor(random() * 100)::INT)
      RETURNING STAT_ID INTO stat_id_val;

      -- Insert DICOM
      INSERT INTO DICOMS (DICOM_NAME, STAT_ID)
      VALUES ('dicom_' || i || '_' || j, stat_id_val)
      RETURNING DICOM_ID INTO dicom_id_val;

      -- Link patient ↔ dicom
      INSERT INTO PATIENTDICOMS (PATIENT_ID, DICOM_ID)
      VALUES (aid_val, dicom_id_val);

      -- For each DICOM: 5 slices
      FOR k IN 1..5 LOOP
        INSERT INTO FILERECORDS (FILETYPE, OBJECT_KEY)
        VALUES (
          'slice',
          's3://bucket/user_' || i || '/dicom_' || j || '/slice_' || k || '.dcm'
        )
        RETURNING FILE_ID INTO file_id_val;

        -- link dicom ↔ file
        INSERT INTO DICOMFILES (DICOM_ID, FILE_ID)
        VALUES (dicom_id_val, file_id_val);

        -- link patient ↔ file
        INSERT INTO PATIENTFILES (FILE_ID, AID)
        VALUES (file_id_val, aid_val);
      END LOOP;
    END LOOP;
  END LOOP;
END $$;
