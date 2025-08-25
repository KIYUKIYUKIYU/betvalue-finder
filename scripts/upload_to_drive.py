#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import json
import glob
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

def upload_to_drive(file_path):
    """Google Driveにファイルをアップロード（修正版）"""
    
    # 環境変数から認証情報を取得
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    
    if not creds_json:
        print("❌ Error: GOOGLE_CREDENTIALS not found")
        return False
    
    if not folder_id:
        print("❌ Error: GOOGLE_DRIVE_FOLDER_ID not found")
        return False
    
    try:
        # 認証情報をパース
        creds_dict = json.loads(creds_json)
        
        # サービスアカウント認証（スコープを修正）
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/drive']  # drive.fileからdriveに変更
        )
        
        # Drive APIサービスを構築
        service = build('drive', 'v3', credentials=creds)
        
        # ファイル名を取得
        file_name = os.path.basename(file_path)
        
        # 既存ファイルを検索して削除
        query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        existing_files = results.get('files', [])
        
        for file in existing_files:
            try:
                service.files().delete(fileId=file['id']).execute()
                print(f"🗑️ Deleted existing file: {file['name']}")
            except:
                pass  # 削除できなくても続行
        
        # ファイルメタデータ（重要: parentsを正しく設定）
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]  # 共有フォルダを親として指定
        }
        
        # ファイルをアップロード
        media = MediaFileUpload(
            file_path,
            mimetype='text/plain',
            resumable=True
        )
        
        # supportsAllDrivesパラメータを追加
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink',
            supportsAllDrives=True  # 共有ドライブをサポート
        ).execute()
        
        print(f"✅ File uploaded successfully!")
        print(f"   Name: {file.get('name')}")
        print(f"   ID: {file.get('id')}")
        print(f"   Link: {file.get('webViewLink')}")
        
        return True
        
    except HttpError as e:
        print(f"❌ HTTP Error: {e}")
        # より詳細なエラー情報
        if e.resp.status == 403:
            print("💡 ヒント: フォルダの共有設定を確認してください")
            print("   1. Google DriveでMLB_Reportsフォルダを右クリック")
            print("   2. 共有 → mlb-report-uploader@mlb-report-system.iam.gserviceaccount.com")
            print("   3. 権限を「編集者」に設定")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """メイン処理"""
    print("=" * 60)
    print("Google Drive Upload Script")
    print("=" * 60)
    
    # daily_reportsフォルダの最新ファイルを取得
    reports = glob.glob("daily_reports/MLB*.txt")
    
    if not reports:
        print("❌ No MLB report files found")
        sys.exit(1)
    
    # 最新のファイルを選択
    latest_report = max(reports, key=os.path.getctime)
    print(f"📄 Found report: {latest_report}")
    
    # アップロード実行
    if upload_to_drive(latest_report):
        print("\n🎉 Upload completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Upload failed")
        sys.exit(1)

if __name__ == "__main__":
    main()