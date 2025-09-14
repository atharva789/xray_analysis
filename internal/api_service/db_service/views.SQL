-- fetch DICOM_IDS by PatientID
-- fetch Dicom images by patient ID
-- fetch patient stats by patient IDs

CREATE OR REPLACE VIEW [patient_files_n_stats_by_dicom] AS 
SELECT 
  pd.AID, pd.DICOM_ID, d.DICOM_NAME, D.CREATED_AT, df.FILE_ID, f.FILETYPE, f.OBJECT_KEY, ps.AGASTON_SCORE
FROM PATIENTDICOMS pd
JOIN DICOMFILES df
  ON pd.DICOM_ID = df.DICOM_ID
JOIN DICOMS d 
  ON d.DICOM_ID = df.DICOM_ID
JOIN FILERECORDS f
  ON f.FILE_ID = df.FILE_ID
JOIN PATIENTSTATS ps
  ON ps.STAT_ID = d.STAT_ID;