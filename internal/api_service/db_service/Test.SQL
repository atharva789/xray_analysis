-- This script populates the database, ensuring all 50 accounts become patients
-- and each patient receives 1 to 3 DICOM studies with 60 slices and 1 mask each.
DO $$
DECLARE
    -- MODIFIED: Configuration updated to your requirements
    v_num_patients INT := 50;
    v_num_slices_per_study INT := 60;
    v_studies_per_patient INT;

    -- Loop variables
    v_patient_aid INT;
    v_dicom_id INT;
    v_stat_id INT;
    v_file_id INT;
    v_file_loop_index INT;
    v_file_type VARCHAR;
    v_object_key VARCHAR;
BEGIN
    RAISE NOTICE 'Starting data generation for 50 patients...';

    -- Step 1: Populate the PATIENTS table for all 50 accounts
    -- RAISE NOTICE '  -> Populating PATIENTS...';
    -- FOR v_patient_aid IN 1..v_num_patients LOOP
    --     INSERT INTO PATIENTS (AID, MRN)
    --     VALUES (v_patient_aid, 100000 + v_patient_aid * 10 + floor(random() * 10));
    -- END LOOP;

    -- Step 2 & 3: Loop through each patient to generate their studies and links
    RAISE NOTICE '  -> Generating studies and files for each patient...';
    FOR v_patient_aid IN 1..v_num_patients LOOP
        -- Assign a random number of studies (1, 2, or 3) to this patient
        v_studies_per_patient := floor(random() * 3 + 1);
        
        RAISE NOTICE '    -> Assigning % studies to patient AID %', v_studies_per_patient, v_patient_aid;

        FOR i IN 1..v_studies_per_patient LOOP
            -- Create a patient stat record
            INSERT INTO PATIENT_STATS (AGASTON_SCORE)
            VALUES (floor(random() * 800))
            RETURNING STAT_ID INTO v_stat_id;

            -- Create the main DICOM record
            INSERT INTO DICOMS (DICOM_NAME, STAT_ID)
            VALUES ('Study ' || substr(md5(random()::text), 1, 8), v_stat_id)
            RETURNING DICOM_ID INTO v_dicom_id;

            -- Link this new DICOM study directly to the current patient
            INSERT INTO PATIENTDICOMS (PATIENT_ID, DICOM_ID)
            VALUES (v_patient_aid, v_dicom_id);

            -- Create file records (60 slices and 1 mask)
            FOR v_file_loop_index IN 1..(v_num_slices_per_study + 1) LOOP
                -- The last file is the mask
                IF v_file_loop_index > v_num_slices_per_study THEN
                    v_file_type := 'mask';
                    v_object_key := 'masks/dicom_' || v_dicom_id || '/mask_' || substr(md5(random()::text), 1, 12) || '.nii.gz';
                ELSE
                    v_file_type := 'slice';
                    v_object_key := 'slices/dicom_' || v_dicom_id || '/slice_' || v_file_loop_index || '.dcm';
                END IF;

                -- Insert the file record
                INSERT INTO FILERECORDS (FILETYPE, OBJECT_KEY)
                VALUES (v_file_type, v_object_key)
                RETURNING FILE_ID INTO v_file_id;

                -- Link the file to the DICOM study
                INSERT INTO DICOMFILES (DICOM_ID, FILE_ID)
                VALUES (v_dicom_id, v_file_id);

                -- Link the file directly to the patient
                INSERT INTO PATIENTFILES (AID, FILE_ID)
                VALUES (v_patient_aid, v_file_id);
            END LOOP;
        END LOOP;
    END LOOP;

    RAISE NOTICE 'Data generation complete.';
END $$;