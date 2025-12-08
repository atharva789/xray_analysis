"""baseline schema

Revision ID: 39a4f87c30f1
Revises: 
Create Date: 2025-09-21 02:00:11.268329

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39a4f87c30f1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "accounts",
        sa.Column("aid", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("fname", sa.String(length=100), nullable=False),
        sa.Column("lname", sa.String(length=100), nullable=False),
        sa.Column("pswrd_hash", sa.LargeBinary(), nullable=False),
        sa.Column("dob", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("username", name="uq_accounts_username"),
        sa.UniqueConstraint("email", name="uq_accounts_email"),
    )

    op.create_table(
        "patients",
        sa.Column("aid", sa.Integer(), primary_key=True),
        sa.Column("mrn", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["aid"], ["accounts.aid"], ondelete="CASCADE"),
        sa.UniqueConstraint("mrn", name="uq_patients_mrn"),
    )

    op.create_table(
        "filerecords",
        sa.Column("file_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("filetype", sa.String(length=50), nullable=False),
        sa.Column("object_key", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "filetype IN ('slice', 'mask')", name="ck_filerecords_filetype"
        ),
    )

    op.create_table(
        "patient_stats",
        sa.Column("stat_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agaston_score", sa.Integer(), nullable=True),
    )

    op.create_table(
        "dicoms",
        sa.Column("dicom_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dicom_name", sa.String(length=100), nullable=False),
        sa.Column("stat_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["stat_id"], ["patient_stats.stat_id"]),
    )

    op.create_table(
        "dicomfiles",
        sa.Column("dicom_id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["dicom_id"], ["dicoms.dicom_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["file_id"], ["filerecords.file_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("dicom_id", "file_id"),
    )

    op.create_table(
        "patientdicoms",
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("dicom_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.aid"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["dicom_id"], ["dicoms.dicom_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("patient_id", "dicom_id"),
    )

    op.create_table(
        "patientfiles",
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("aid", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["file_id"], ["filerecords.file_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["aid"], ["patients.aid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("file_id", "aid"),
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW patient_files_n_stats_by_dicom AS
        SELECT
          pd.patient_id,
          pd.dicom_id,
          d.dicom_name,
          d.created_at,
          df.file_id,
          f.filetype,
          f.object_key,
          ps.agaston_score
        FROM patientdicoms pd
        JOIN dicomfiles df ON pd.dicom_id = df.dicom_id
        JOIN dicoms d ON d.dicom_id = df.dicom_id
        JOIN filerecords f ON f.file_id = df.file_id
        JOIN patient_stats ps ON ps.stat_id = d.stat_id;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW patient_accessions AS
        SELECT
          d.dicom_id,
          d.dicom_name,
          d.created_at,
          ps.agaston_score,
          fr.object_key
        FROM patientdicoms pd
        JOIN dicoms d ON pd.dicom_id = d.dicom_id
        JOIN patient_stats ps ON ps.stat_id = d.stat_id
        JOIN dicomfiles df ON df.dicom_id = d.dicom_id
        JOIN filerecords fr ON fr.file_id = df.file_id;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION get_dicoms_by_aid(aid_input INT)
        RETURNS TABLE (
          dicom_id INT,
          dicom_name VARCHAR,
          created_at TIMESTAMP,
          agaston_score INT
        ) AS $$
        BEGIN
          RETURN QUERY
            SELECT
              px.dicom_id,
              px.dicom_name,
              px.created_at,
              px.agaston_score
            FROM patient_files_n_stats_by_dicom px
            WHERE px.patient_id = aid_input;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION get_accession(aid_input INT, dicom_id_input INT)
        RETURNS TABLE (
          dicom_name VARCHAR,
          created_at TIMESTAMP,
          filetype VARCHAR,
          object_key VARCHAR,
          agaston_score INT
        ) AS $$
        BEGIN
          RETURN QUERY
            SELECT
              d.dicom_name,
              d.created_at,
              d.filetype,
              d.object_key,
              d.agaston_score
            FROM patient_files_n_stats_by_dicom d
            WHERE d.patient_id = aid_input AND d.dicom_id = dicom_id_input;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP FUNCTION IF EXISTS get_accession(INT, INT);")
    op.execute("DROP FUNCTION IF EXISTS get_dicoms_by_aid(INT);")
    op.execute("DROP VIEW IF EXISTS patient_accessions;")
    op.execute("DROP VIEW IF EXISTS patient_files_n_stats_by_dicom;")

    op.drop_table("patientfiles")
    op.drop_table("patientdicoms")
    op.drop_table("dicomfiles")
    op.drop_table("dicoms")
    op.drop_table("patient_stats")
    op.drop_table("filerecords")
    op.drop_table("patients")
    op.drop_table("accounts")
