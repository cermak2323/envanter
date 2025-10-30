"""
QR Kod Yönetim Paneli - Admin İşlemleri
- Yeni QR kod üret
- QR kodları listele
- CSV import (mevcut QR'ları korur, sadece yenileri ekler)
- PDF export
"""

import uuid
import csv
from io import StringIO, BytesIO
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

from models import db, PartCode, QRCode, CountSession
from b2_storage import upload_qr_to_b2, generate_qr_code_image


qr_admin_bp = Blueprint('qr_admin', __name__, url_prefix='/admin/qr')


@qr_admin_bp.route('/generate', methods=['GET', 'POST'])
def generate_qr():
    """Yeni QR kod oluştur"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            part_code = data.get('part_code', '').strip()
            part_name = data.get('part_name', '').strip()
            
            if not part_code or not part_name:
                return jsonify({'success': False, 'message': 'Part code ve isim gerekli'}), 400
            
            # Mevcut part code'u kontrol et, yoksa oluştur
            part = PartCode.query.filter_by(part_code=part_code).first()
            if not part:
                part = PartCode(part_code=part_code, part_name=part_name)
                db.session.add(part)
                db.session.commit()
                print(f"✅ Yeni part code oluşturuldu: {part_code}")
            
            # Yeni QR kod oluştur
            qr_id = f"{part_code}-{str(uuid.uuid4())[:8]}"
            
            # QR resmi oluştur
            qr_image = generate_qr_code_image(qr_id)
            
            # B2'ye yükle (kalıcı URL)
            blob_url, file_id = upload_qr_to_b2(
                qr_image, 
                f"qr-permanent/{qr_id}.png",
                file_name=f"{qr_id}.png"
            )
            
            # Veritabanına ekle
            qr_code = QRCode(
                qr_id=qr_id,
                part_code_id=part.id,
                blob_url=blob_url,
                blob_file_id=file_id
            )
            db.session.add(qr_code)
            db.session.commit()
            
            print(f"✅ QR kod oluşturuldu: {qr_id} -> {blob_url[:50]}...")
            
            return jsonify({
                'success': True,
                'message': f'QR kod başarıyla oluşturuldu',
                'qr_id': qr_id,
                'part_code': part_code,
                'part_name': part_name,
                'blob_url': blob_url
            }), 201
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ QR oluşturma hatası: {str(e)}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return render_template('admin_qr_generate.html')


@qr_admin_bp.route('/list', methods=['GET'])
def list_qrcodes():
    """Tüm QR kodları listele"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Sayfalı sonuçlar
        qr_codes = QRCode.query.join(PartCode).paginate(
            page=page, 
            per_page=per_page,
            error_out=False
        )
        
        items = []
        for qr in qr_codes.items:
            items.append({
                'id': qr.id,
                'qr_id': qr.qr_id,
                'part_code': qr.part.part_code,
                'part_name': qr.part.part_name,
                'is_used': qr.is_used,
                'used_count': qr.used_count,
                'blob_url': qr.blob_url,
                'created_at': qr.created_at.isoformat(),
                'first_used_at': qr.first_used_at.isoformat() if qr.first_used_at else None
            })
        
        return jsonify({
            'success': True,
            'items': items,
            'total': qr_codes.total,
            'pages': qr_codes.pages,
            'current_page': page
        })
        
    except Exception as e:
        print(f"❌ QR listeme hatası: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@qr_admin_bp.route('/import-csv', methods=['POST'])
def import_csv():
    """CSV dosyasından part code'ları import et (mevcut QR'ları korur)"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Dosya gerekli'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Dosya seçilmedi'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'message': 'Sadece CSV dosyaları kabul edilir'}), 400
        
        # CSV oku
        stream = StringIO(file.stream.read().decode('utf-8'))
        reader = csv.DictReader(stream)
        
        new_parts = 0
        existing_parts = 0
        
        for row in reader:
            part_code = row.get('part_code', '').strip()
            part_name = row.get('part_name', '').strip()
            
            if not part_code:
                continue
            
            # Mevcut part code'u kontrol et
            existing = PartCode.query.filter_by(part_code=part_code).first()
            if existing:
                existing_parts += 1
                print(f"⏭️ Mevcut part code atlandı: {part_code}")
                continue
            
            # Yeni part code ekle
            part = PartCode(
                part_code=part_code,
                part_name=part_name or part_code
            )
            db.session.add(part)
            new_parts += 1
        
        db.session.commit()
        
        message = f"✅ Import tamamlandı: {new_parts} yeni, {existing_parts} mevcut"
        print(message)
        
        return jsonify({
            'success': True,
            'message': message,
            'new_count': new_parts,
            'existing_count': existing_parts
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ CSV import hatası: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@qr_admin_bp.route('/export-pdf', methods=['GET'])
def export_pdf():
    """Tüm QR kodları PDF olarak indir"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Image, Table, TableStyle, Paragraph, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        
        # QR kodları çek
        qr_codes = QRCode.query.join(PartCode).all()
        
        # PDF belleğe oluştur
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        elements = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='#333333',
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # Başlık
        title = Paragraph("QR Kodlar - Envanter", title_style)
        elements.append(title)
        
        # Tablo verisi
        table_data = [['QR ID', 'Part Code', 'Part Name', 'Durum']]
        
        for qr in qr_codes:
            status = '✓ Kullanıldı' if qr.is_used else '○ Beklemede'
            table_data.append([
                qr.qr_id[:30],
                qr.part.part_code,
                qr.part.part_name[:30],
                status
            ])
        
        # Tablo oluştur
        table = Table(table_data, colWidths=[80*mm, 40*mm, 40*mm, 25*mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), '#4CAF50'),
            ('TEXTCOLOR', (0, 0), (-1, 0), 'white'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), '#f0f0f0'),
            ('GRID', (0, 0), (-1, -1), 1, 'black'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        elements.append(table)
        
        # PDF oluştur
        doc.build(elements)
        pdf_buffer.seek(0)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'qr-codes-{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        
    except Exception as e:
        print(f"❌ PDF export hatası: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@qr_admin_bp.route('/stats', methods=['GET'])
def get_stats():
    """QR istatistikleri"""
    try:
        total_qr = QRCode.query.count()
        used_qr = QRCode.query.filter_by(is_used=True).count()
        unused_qr = total_qr - used_qr
        
        total_parts = PartCode.query.count()
        
        return jsonify({
            'success': True,
            'total_qr': total_qr,
            'used_qr': used_qr,
            'unused_qr': unused_qr,
            'total_parts': total_parts,
            'usage_percentage': round((used_qr / total_qr * 100) if total_qr > 0 else 0, 2)
        })
        
    except Exception as e:
        print(f"❌ Stats hatası: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500
