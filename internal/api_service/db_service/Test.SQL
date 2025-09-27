DELETE FROM PATIENTS WHERE MRN BETWEEN 100001 AND 100050;
DELETE FROM ACCOUNTS WHERE USERNAME LIKE 'user%';

DO $$
BEGIN
    FOR i IN 1..50 LOOP
        INSERT INTO ACCOUNTS (USERNAME, EMAIL, FNAME, LNAME, PSWRD_HASH, DOB)
        VALUES (
            'user' || i,
            'user' || i || '@example.com',
            'First' || i,
            'Last' || i,
            digest('password' || i, 'sha256')::bytea, -- hashed password
            DATE '1980-01-01' + (i || ' days')::interval
        );
    END LOOP;
END$$;

INSERT INTO PATIENTS (AID, MRN)
SELECT AID, 100000 + AID
FROM ACCOUNTS
WHERE USERNAME LIKE 'user%';
