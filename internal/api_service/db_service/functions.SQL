CREATE OR REPLACE FUNCTION get_dicoms_by_aid(aid_input INT)
RETURNS TABLE (
  DICOM_ID INT,
  DICOM_NAME VARCHAR,
  CREATED_AT TIMESTAMP,
  AGASTON_SCORE INT
) AS $$
BEGIN
  RETURN QUERY
    SELECT
      px.DICOM_ID,
      px.DICOM_NAME,
      px.CREATED_AT,
      px.AGASTON_SCORE
    FROM
      patient_files_n_stats_by_dicom px
    WHERE
      px.PATIENT_ID = aid_input;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_accession(aid_input INT, dicom_id_input INT)
RETURNS TABLE (
  DICOM_NAME VARCHAR,
  CREATED_AT TIMESTAMP,
  FILETYPE VARCHAR,
  OBJECT_KEY VARCHAR,
  AGASTON_SCORE INT
) AS $$
BEGIN
  RETURN QUERY
    SELECT 
      D.DICOM_NAME,
      D.CREATED_AT,
      D.FILETYPE,
      D.OBJECT_KEY,
      D.AGASTON_SCORE
    FROM
      patient_files_n_stats_by_dicom D
    WHERE
      D.PATIENT_ID = aid_input AND D.dicom_id = dicom_id_input;
END;
$$ LANGUAGE plpgsql;