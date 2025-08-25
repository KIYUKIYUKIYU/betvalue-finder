#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HTMLレポートをPDFに変換するスクリプト（pdfkit版）
"""
import os
import sys
from pathlib import Path
from datetime import datetime

def convert_html_to_pdf_with_pdfkit(html_file_path, output_dir=None):
    """pdfkitを使用してHTMLをPDFに変換"""
    try:
        import pdfkit
    except ImportError:
        print("❌ pdfkitがインストールされていません")
        print("   実行: pip install pdfkit")
        return None
    
    # 出力ディレクトリの設定
    if output_dir is None:
        output_dir = Path(html_file_path).parent.parent / "pdf"
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # PDFファイル名を生成
    html_path = Path(html_file_path)
    pdf_filename = html_path.stem + ".pdf"
    pdf_path = output_dir / pdf_filename
    
    print(f"📄 Converting HTML to PDF using pdfkit...")
    print(f"   Input: {html_file_path}")
    print(f"   Output: {pdf_path}")
    
    # wkhtmltopdfの設定
    config = None
    # Windowsの一般的なインストールパス
    wkhtmltopdf_paths = [
        r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
        r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe',
        r'C:\wkhtmltopdf\bin\wkhtmltopdf.exe',
    ]
    
    for path in wkhtmltopdf_paths:
        if os.path.exists(path):
            config = pdfkit.configuration(wkhtmltopdf=path)
            print(f"✅ wkhtmltopdf found: {path}")
            break
    
    if config is None:
        print("⚠️ wkhtmltopdfが見つかりません")
        print("   https://wkhtmltopdf.org/downloads.html からダウンロードしてください")
        print("   インストール後、パスを確認してください")
        # configなしで試す（PATHに登録されている場合）
    
    # PDFオプション
    options = {
        'page-size': 'A4',
        'margin-top': '15mm',
        'margin-right': '15mm',
        'margin-bottom': '15mm',
        'margin-left': '15mm',
        'encoding': "UTF-8",
        'enable-local-file-access': None,
        'no-outline': None
    }
    
    try:
        # PDFに変換
        pdfkit.from_file(
            str(html_file_path),
            str(pdf_path),
            options=options,
            configuration=config
        )
        print(f"✅ PDF created successfully: {pdf_path}")
        return str(pdf_path)
        
    except Exception as e:
        print(f"❌ Error converting to PDF: {e}")
        return None

def convert_html_to_pdf_simple(html_file_path, output_dir=None):
    """シンプルなPDF変換（ブラウザ印刷の代替）"""
    import webbrowser
    
    # 出力ディレクトリの設定
    if output_dir is None:
        output_dir = Path(html_file_path).parent.parent / "pdf"
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # HTMLファイルをブラウザで開く
    html_path = Path(html_file_path).resolve()
    print(f"📄 HTMLファイルをブラウザで開きます...")
    print(f"   {html_path}")
    print()
    print("🖨️ ブラウザから手動でPDFとして保存してください:")
    print("   1. Ctrl+P で印刷ダイアログを開く")
    print("   2. プリンターで「PDFとして保存」を選択")
    print(f"   3. 保存先: {output_dir}")
    print()
    
    webbrowser.open(str(html_path))
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_to_pdf.py <html_file>")
        print("Example: python convert_to_pdf.py daily_reports/html/MLB08月22日(金)レポート.html")
        sys.exit(1)
    
    html_file = sys.argv[1]
    
    if not os.path.exists(html_file):
        print(f"❌ File not found: {html_file}")
        sys.exit(1)
    
    print("PDF変換方法を選択してください:")
    print("1. pdfkit (wkhtmltopdf必要)")
    print("2. ブラウザで開く（手動でPDF保存）")
    print()
    
    choice = input("選択 (1 or 2): ").strip()
    
    if choice == "1":
        result = convert_html_to_pdf_with_pdfkit(html_file)
        if result:
            print(f"✅ Conversion complete: {result}")
        else:
            print("❌ 変換に失敗しました。方法2を試してください。")
    else:
        convert_html_to_pdf_simple(html_file)

if __name__ == "__main__":
    main()