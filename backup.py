import os
import json
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import date
import gzip
import subprocess

def list_postgres_databases(host, database_name, port, user, password):
    try:
        process = subprocess.Popen(
            ['psql',
             '--dbname=postgresql://{}:{}@{}:{}/{}'.format(user, password, host, port, database_name),
             '--list'],
            stdout=subprocess.PIPE
        )
        output = process.communicate()[0]
        if int(process.returncode) != 0:
            print('Command failed. Return code : {}'.format(process.returncode))
            exit(1)
        return output
    except Exception as e:
        print(e)
        exit(1)

def write_to_drive(path, filename):
    json_secret = json.loads(os.environ.get('GOOGLE_JSON_KEY'))
    # google_drive_folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    google_drive_folder_id = ''

    scope = ["https://www.googleapis.com/auth/drive"]

    credentials = ServiceAccountCredentials.from_json_keyfile_dict(keyfile_dict=json_secret, scopes=scope)
    print(credentials)

    # setup the google drive stance and sign in
    drive = build('drive', 'v3', credentials=credentials)

    backups_folder_id = drive.files().list(
        # corpora="drive",
        # driveId=google_drive_folder_id,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        q="name='UNC-NCSU SunnyD Backups' and mimeType='application/vnd.google-apps.folder'"
    ).execute().get('files')[0].get('id')

    file_metadata = {
            'name': [filename],
            'parents': [backups_folder_id]
        }
    media = MediaFileUpload(path,
                            mimetype='application/x-gzip-compressed',
                            resumable=True)

    print("ATTEMPTING UPLOAD")
    file = drive.files().create(body=file_metadata,
                                media_body=media,
                                supportsAllDrives=True).execute()
    print("UPLOAD SUCCESSFUL")
    print(file)

def backup_postgres_db(host, database_name, port, user, password, dest_file, verbose):
    """
    Backup postgres db to a file.
    """
    if verbose:
        try:
            process = subprocess.Popen(
                ['pg_dump',
                 '--dbname=postgresql://{}:{}@{}:{}/{}'.format(user, password, host, port, database_name),
                 '-Ft',
                 '-f', dest_file,
                 '-v'],
                stdout=subprocess.PIPE
            )
            output = process.communicate()[0]
            if int(process.returncode) != 0:
                print('Command failed. Return code : {}'.format(process.returncode))
                exit(1)
            return output
        except Exception as e:
            print(e)
            exit(1)
    else:

        try:
            process = subprocess.Popen(
                ['pg_dump',
                 '--dbname=postgresql://{}:{}@{}:{}/{}'.format(user, password, host, port, database_name),
                 '-Ft'
                '-n', 'public'
                 '-f', dest_file],
                stdout=subprocess.PIPE
            )
            output = process.communicate()[0]
            if process.returncode != 0:
                print('Command failed. Return code : {}'.format(process.returncode))
                exit(1)
            return output
        except Exception as e:
            print(e)
            exit(1)

def compress_file(src_file):
    print("COMPRESSING FILE " + src_file)
    compressed_file = "{}.gz".format(str(src_file))
    with open(src_file, 'rb') as f_in:
        with gzip.open(compressed_file, 'wb') as f_out:
            for line in f_in:
                f_out.write(line)
    return compressed_file

def main():
    db_host = os.environ.get('POSTGRESQL_HOSTNAME')
    db_user = os.environ.get('POSTGRESQL_USER')
    db_name = os.environ.get('POSTGRESQL_DATABASE')
    db_pw = os.environ.get('POSTGRESQL_PASSWORD')

    filename = "sdfp-db-" + date.today().strftime("%Y-%m-%d") + ".tar"
    path = "/tmp/" + filename
    # dbs = list_postgres_databases(db_host, db_name, 5432, db_user, db_pw)
    backup_postgres_db(db_host, db_name, 5432, db_user, db_pw, path, True)
    compress_file(path)
    path += ".gz"
    filename += ".gz"
    write_to_drive(path, filename)

if __name__ == "__main__":
    main()