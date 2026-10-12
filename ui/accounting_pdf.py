# ui/accounting_pdf.py
# ============================================================
# تولید PDF و چاپ برای اسناد حسابداری — نسخه 1.1
# ============================================================
# پشتیبانی از:
# ✅ سند حسابداری تکی (با اقلام کامل)
# ✅ دفتر روزنامه (با صفحه‌بندی خودکار)
# ✅ دفتر کل (خلاصه یا تفصیلی)
# ✅ چاپ فیزیکی (QPrinter) — با اندازه صحیح
# ✅ پشتیبانی کامل از فارسی
# ✅ قالب رسمی با هدر شرکت
# ============================================================

import os
import logging
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog, QPrintDialog
from PyQt5.QtGui import QTextDocument
from PyQt5.QtCore import QMarginsF, QSizeF, QSize

logger = logging.getLogger(__name__)


# ============================================================
# ========== Import های اختیاری ==========
# ============================================================

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, PageBreak
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("ReportLab نصب نیست. pip install reportlab")

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    PERSIAN_SUPPORT = True
except ImportError:
    PERSIAN_SUPPORT = False
    logger.warning("arabic-reshaper نصب نیست. pip install arabic-reshaper python-bidi")


# ============================================================
# ========== توابع کمکی ==========
# ============================================================

def _find_font_path() -> str:
    """پیدا کردن مسیر فونت فارسی"""
    candidates = [
        "fonts/tahoma.ttf",
        "fonts/Vazir.ttf",
        "fonts/B Nazanin.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    
    for path in candidates:
        if os.path.exists(path):
            return path
    
    project_root = Path(__file__).parent.parent
    for font_file in project_root.rglob("*.ttf"):
        return str(font_file)
    
    return ""


def _fa(text) -> str:
    """تبدیل متن فارسی به شکل صحیح برای ReportLab"""
    if text is None:
        return ""
    
    text = str(text)
    
    if not PERSIAN_SUPPORT:
        return text
    
    try:
        import re
        parts = re.split(r'([0-9]+|[a-zA-Z]+)', text)
        result = []
        
        for part in parts:
            if part.isdigit() or (part.isalpha() and part.isascii()):
                result.append(part)
            elif part.strip():
                try:
                    reshaped = arabic_reshaper.reshape(part)
                    result.append(reshaped)
                except Exception:
                    result.append(part)
            else:
                result.append(part)
        
        final_text = ''.join(result)
        return get_display(final_text)
    except Exception as e:
        logger.warning(f"خطا در تبدیل فارسی: {e}")
        return text


# ============================================================
# ========== کلاس اصلی ==========
# ============================================================

class AccountingPDFGenerator:
    """تولید PDF و چاپ برای اسناد حسابداری"""
    
    def __init__(self, company_info: dict = None):
        self.company_info = company_info or self._default_company_info()
        self.font_path = _find_font_path()
        self.font_name = 'PersianFont'
        
        if self.font_path and PDF_AVAILABLE:
            try:
                pdfmetrics.registerFont(TTFont(self.font_name, self.font_path))
            except Exception as e:
                logger.warning(f"خطا در ثبت فونت: {e}")
    
    @staticmethod
    def _default_company_info() -> dict:
        return {
            'company_name': 'شرکت حسابداری',
            'company_economic': '',
            'company_phone': '',
            'company_address': '',
        }
    
    # ============================================================
    # استایل‌های پایه
    # ============================================================
    
    def _get_styles(self):
        styles = getSampleStyleSheet()
        
        return {
            'title': ParagraphStyle(
                'Title', parent=styles['Normal'],
                fontName=self.font_name, fontSize=16,
                alignment=TA_CENTER, leading=22,
                textColor=colors.Color(0.15, 0.17, 0.46),
                spaceAfter=6,
            ),
            'subtitle': ParagraphStyle(
                'Subtitle', parent=styles['Normal'],
                fontName=self.font_name, fontSize=11,
                alignment=TA_CENTER, leading=16,
                textColor=colors.Color(0.3, 0.3, 0.3),
            ),
            'header': ParagraphStyle(
                'Header', parent=styles['Normal'],
                fontName=self.font_name, fontSize=10,
                alignment=TA_CENTER, leading=14,
                textColor=colors.Color(0.4, 0.4, 0.4),
            ),
            'right': ParagraphStyle(
                'Right', parent=styles['Normal'],
                fontName=self.font_name, fontSize=10,
                alignment=TA_RIGHT, leading=16,
            ),
            'center': ParagraphStyle(
                'Center', parent=styles['Normal'],
                fontName=self.font_name, fontSize=10,
                alignment=TA_CENTER, leading=14,
            ),
            'footer': ParagraphStyle(
                'Footer', parent=styles['Normal'],
                fontName=self.font_name, fontSize=8,
                alignment=TA_CENTER, leading=12,
                textColor=colors.Color(0.5, 0.5, 0.5),
            ),
        }
    
    # ============================================================
    # هدر و فوتر
    # ============================================================
    
    def _build_header(self, title: str, subtitle: str = "") -> list:
        elements = []
        
        company_name = self.company_info.get('company_name', 'شرکت')
        company_economic = self.company_info.get('company_economic', '')
        company_phone = self.company_info.get('company_phone', '')
        company_address = self.company_info.get('company_address', '')
        
        styles = self._get_styles()
        
        elements.append(Paragraph(
            _fa(company_name), styles['title']
        ))
        
        info_parts = []
        if company_economic:
            info_parts.append(f"کد اقتصادی: {company_economic}")
        if company_phone:
            info_parts.append(f"تلفن: {company_phone}")
        
        if info_parts:
            elements.append(Paragraph(
                _fa(' | '.join(info_parts)), styles['header']
            ))
        
        if company_address:
            elements.append(Paragraph(
                _fa(f"آدرس: {company_address}"), styles['header']
            ))
        
        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph(_fa(title), styles['title']))
        
        if subtitle:
            elements.append(Paragraph(_fa(subtitle), styles['subtitle']))
        
        elements.append(Spacer(1, 5 * mm))
        
        return elements
    
    def _build_footer(self, canvas_obj, doc):
        canvas_obj.saveState()
        
        footer_text = f"تاریخ چاپ: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
        canvas_obj.setFont(self.font_name, 8)
        canvas_obj.setFillColor(colors.Color(0.5, 0.5, 0.5))
        
        canvas_obj.drawString(20 * mm, 10 * mm, _fa(footer_text))
        canvas_obj.drawCentredString(A4[0] / 2, 10 * mm, _fa(f"صفحه {doc.page}"))
        canvas_obj.drawRightString(
            A4[0] - 20 * mm, 10 * mm,
            _fa("ImanAccount - حسابداری هوشمند")
        )
        
        canvas_obj.restoreState()
    
    # ============================================================
    # PDF سند حسابداری
    # ============================================================
    
    def generate_voucher_pdf(self, voucher: dict, items: list, output_path: str) -> bool:
        if not PDF_AVAILABLE:
            logger.error("ReportLab نصب نیست")
            return False
        
        try:
            doc = SimpleDocTemplate(
                output_path, pagesize=A4,
                rightMargin=15 * mm, leftMargin=15 * mm,
                topMargin=15 * mm, bottomMargin=20 * mm,
            )
            
            styles = self._get_styles()
            elements = []
            
            elements.extend(self._build_header(
                "سند حسابداری",
                f"شماره: {voucher.get('voucher_no', '')}"
            ))
            
            date = voucher.get('date', '')
            description = voucher.get('description', '')
            vtype = voucher.get('type', 'عادی')
            
            info_data = [
                [
                    Paragraph(_fa(f"شماره سند: {voucher.get('voucher_no', '')}"), styles['right']),
                    Paragraph(_fa(f"تاریخ: {date}"), styles['right']),
                ],
                [
                    Paragraph(_fa(f"نوع سند: {vtype}"), styles['right']),
                    Paragraph(_fa(""), styles['right']),
                ],
                [
                    Paragraph(_fa(f"شرح: {description}"), styles['right']),
                    Paragraph(_fa(""), styles['right']),
                ],
            ]
            
            info_table = Table(info_data, colWidths=[doc.width / 2.0] * 2)
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.96, 0.96, 0.96)),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 5 * mm))
            
            items_data = [[
                Paragraph(_fa("ردیف"), styles['center']),
                Paragraph(_fa("کد حساب"), styles['center']),
                Paragraph(_fa("نام حساب"), styles['center']),
                Paragraph(_fa("شرح"), styles['center']),
                Paragraph(_fa("بدهکار"), styles['center']),
                Paragraph(_fa("بستانکار"), styles['center']),
            ]]
            
            total_debit = 0
            total_credit = 0
            
            for i, item in enumerate(items, 1):
                debit = float(item.get('debit', 0) or 0)
                credit = float(item.get('credit', 0) or 0)
                total_debit += debit
                total_credit += credit
                
                items_data.append([
                    Paragraph(_fa(str(i)), styles['center']),
                    Paragraph(_fa(item.get('account_code', '')), styles['center']),
                    Paragraph(_fa(item.get('account_name', '')), styles['right']),
                    Paragraph(_fa(item.get('description', '') or ''), styles['right']),
                    Paragraph(_fa(f"{debit:,.0f}" if debit else "-"), styles['right']),
                    Paragraph(_fa(f"{credit:,.0f}" if credit else "-"), styles['right']),
                ])
            
            items_data.append([
                Paragraph(_fa(""), styles['center']),
                Paragraph(_fa(""), styles['center']),
                Paragraph(_fa("جمع کل"), styles['right']),
                Paragraph(_fa(""), styles['right']),
                Paragraph(_fa(f"{total_debit:,.0f}"), styles['right']),
                Paragraph(_fa(f"{total_credit:,.0f}"), styles['right']),
            ])
            
            col_widths = [
                doc.width * 0.06,
                doc.width * 0.12,
                doc.width * 0.22,
                doc.width * 0.22,
                doc.width * 0.19,
                doc.width * 0.19,
            ]
            
            items_table = Table(items_data, colWidths=col_widths, repeatRows=1)
            items_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.15, 0.17, 0.46)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.95, 1)),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(items_table)
            elements.append(Spacer(1, 8 * mm))
            
            diff = abs(total_debit - total_credit)
            if diff < 1:
                status_text = "✅ سند موازنه است"
                status_color = colors.green
            else:
                status_text = f"⚠️ عدم موازنه: {diff:,.0f} ریال"
                status_color = colors.red
            
            status_para = Paragraph(
                _fa(status_text),
                ParagraphStyle(
                    'Status', parent=styles['right'],
                    fontSize=12, textColor=status_color,
                )
            )
            elements.append(status_para)
            elements.append(Spacer(1, 15 * mm))
            
            signs_data = [[
                Paragraph(_fa("تهیه‌کننده"), styles['center']),
                Paragraph(_fa("تاییدکننده"), styles['center']),
                Paragraph(_fa("مدیر مالی"), styles['center']),
            ], [
                Paragraph(_fa("\n\n\n"), styles['center']),
                Paragraph(_fa("\n\n\n"), styles['center']),
                Paragraph(_fa("\n\n\n"), styles['center']),
            ]]
            
            signs_table = Table(signs_data, colWidths=[doc.width / 3.0] * 3)
            signs_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(signs_table)
            
            doc.build(
                elements,
                onFirstPage=self._build_footer,
                onLaterPages=self._build_footer,
            )
            
            logger.info(f"✅ PDF سند ذخیره شد: {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"❌ خطا در تولید PDF سند: {e}", exc_info=True)
            return False
    
    # ============================================================
    # PDF دفتر روزنامه
    # ============================================================
    
    def generate_journal_pdf(self, data: list, from_date: str, to_date: str,
                            output_path: str) -> bool:
        if not PDF_AVAILABLE:
            return False
        
        try:
            doc = SimpleDocTemplate(
                output_path, pagesize=A4,
                rightMargin=12 * mm, leftMargin=12 * mm,
                topMargin=15 * mm, bottomMargin=20 * mm,
            )
            
            styles = self._get_styles()
            elements = []
            
            elements.extend(self._build_header(
                "دفتر روزنامه",
                f"از {from_date} تا {to_date}"
            ))
            
            headers = [
                "ردیف", "تاریخ", "شماره سند", "شرح",
                "کد حساب", "نام حساب", "بدهکار", "بستانکار"
            ]
            
            items_data = [[
                Paragraph(_fa(h), styles['center']) for h in headers
            ]]
            
            total_debit = 0
            total_credit = 0
            
            for i, row in enumerate(data, 1):
                debit = float(row.get('debit', 0) or 0)
                credit = float(row.get('credit', 0) or 0)
                total_debit += debit
                total_credit += credit
                
                items_data.append([
                    Paragraph(_fa(str(i)), styles['center']),
                    Paragraph(_fa(str(row.get('date', ''))), styles['center']),
                    Paragraph(_fa(str(row.get('voucher_no', ''))), styles['center']),
                    Paragraph(_fa(str(row.get('description', '') or '')), styles['right']),
                    Paragraph(_fa(str(row.get('account_code', ''))), styles['center']),
                    Paragraph(_fa(str(row.get('account_name', '') or '')), styles['right']),
                    Paragraph(_fa(f"{debit:,.0f}" if debit else "-"), styles['right']),
                    Paragraph(_fa(f"{credit:,.0f}" if credit else "-"), styles['right']),
                ])
            
            items_data.append([
                Paragraph(_fa(""), styles['center']),
                Paragraph(_fa(""), styles['center']),
                Paragraph(_fa(""), styles['center']),
                Paragraph(_fa("جمع کل"), styles['right']),
                Paragraph(_fa(""), styles['center']),
                Paragraph(_fa(""), styles['right']),
                Paragraph(_fa(f"{total_debit:,.0f}"), styles['right']),
                Paragraph(_fa(f"{total_credit:,.0f}"), styles['right']),
            ])
            
            col_widths = [
                doc.width * 0.05,
                doc.width * 0.10,
                doc.width * 0.09,
                doc.width * 0.20,
                doc.width * 0.10,
                doc.width * 0.16,
                doc.width * 0.15,
                doc.width * 0.15,
            ]
            
            table = Table(items_data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.15, 0.17, 0.46)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.95, 1)),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
            ]))
            elements.append(table)
            
            doc.build(
                elements,
                onFirstPage=self._build_footer,
                onLaterPages=self._build_footer,
            )
            
            logger.info(f"✅ PDF دفتر روزنامه ذخیره شد: {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"❌ خطا در PDF دفتر روزنامه: {e}", exc_info=True)
            return False
    
    # ============================================================
    # PDF دفتر کل
    # ============================================================
    
    def generate_ledger_pdf(self, data: list, account_name: str,
                           from_date: str, to_date: str,
                           output_path: str, is_summary: bool = False) -> bool:
        if not PDF_AVAILABLE:
            return False
        
        try:
            doc = SimpleDocTemplate(
                output_path, pagesize=A4,
                rightMargin=12 * mm, leftMargin=12 * mm,
                topMargin=15 * mm, bottomMargin=20 * mm,
            )
            
            styles = self._get_styles()
            elements = []
            
            title = "دفتر کل (خلاصه)" if is_summary else "دفتر کل"
            elements.extend(self._build_header(
                title,
                f"حساب: {account_name} | از {from_date} تا {to_date}"
            ))
            
            if is_summary:
                headers = ["ردیف", "کد حساب", "نام حساب", "نوع", "بدهکار", "بستانکار"]
                
                items_data = [[
                    Paragraph(_fa(h), styles['center']) for h in headers
                ]]
                
                total_debit = 0
                total_credit = 0
                
                type_map = {
                    'asset': 'دارایی', 'liability': 'بدهی',
                    'equity': 'سرمایه', 'income': 'درآمد',
                    'expense': 'هزینه'
                }
                
                for i, row in enumerate(data, 1):
                    debit = float(row.get('total_debit', 0) or 0)
                    credit = float(row.get('total_credit', 0) or 0)
                    total_debit += debit
                    total_credit += credit
                    
                    items_data.append([
                        Paragraph(_fa(str(i)), styles['center']),
                        Paragraph(_fa(str(row.get('code', ''))), styles['center']),
                        Paragraph(_fa(str(row.get('name', ''))), styles['right']),
                        Paragraph(_fa(type_map.get(row.get('type', ''), row.get('type', ''))), styles['center']),
                        Paragraph(_fa(f"{debit:,.0f}" if debit else "-"), styles['right']),
                        Paragraph(_fa(f"{credit:,.0f}" if credit else "-"), styles['right']),
                    ])
                
                items_data.append([
                    Paragraph(_fa(""), styles['center']),
                    Paragraph(_fa(""), styles['center']),
                    Paragraph(_fa("جمع کل"), styles['right']),
                    Paragraph(_fa(""), styles['center']),
                    Paragraph(_fa(f"{total_debit:,.0f}"), styles['right']),
                    Paragraph(_fa(f"{total_credit:,.0f}"), styles['right']),
                ])
                
                col_widths = [
                    doc.width * 0.06,
                    doc.width * 0.14,
                    doc.width * 0.30,
                    doc.width * 0.15,
                    doc.width * 0.175,
                    doc.width * 0.175,
                ]
            
            else:
                headers = ["ردیف", "تاریخ", "شماره سند", "شرح", "بدهکار", "بستانکار", "مانده"]
                
                items_data = [[
                    Paragraph(_fa(h), styles['center']) for h in headers
                ]]
                
                total_debit = 0
                total_credit = 0
                balance = 0
                
                for i, row in enumerate(data, 1):
                    debit = float(row.get('debit', 0) or 0)
                    credit = float(row.get('credit', 0) or 0)
                    total_debit += debit
                    total_credit += credit
                    balance = total_debit - total_credit
                    
                    items_data.append([
                        Paragraph(_fa(str(i)), styles['center']),
                        Paragraph(_fa(str(row.get('date', ''))), styles['center']),
                        Paragraph(_fa(str(row.get('voucher_no', ''))), styles['center']),
                        Paragraph(_fa(str(row.get('description', '') or '')), styles['right']),
                        Paragraph(_fa(f"{debit:,.0f}" if debit else "-"), styles['right']),
                        Paragraph(_fa(f"{credit:,.0f}" if credit else "-"), styles['right']),
                        Paragraph(_fa(f"{balance:,.0f}"), styles['right']),
                    ])
                
                items_data.append([
                    Paragraph(_fa(""), styles['center']),
                    Paragraph(_fa(""), styles['center']),
                    Paragraph(_fa("جمع کل"), styles['right']),
                    Paragraph(_fa(""), styles['right']),
                    Paragraph(_fa(f"{total_debit:,.0f}"), styles['right']),
                    Paragraph(_fa(f"{total_credit:,.0f}"), styles['right']),
                    Paragraph(_fa(f"{balance:,.0f}"), styles['right']),
                ])
                
                col_widths = [
                    doc.width * 0.06,
                    doc.width * 0.12,
                    doc.width * 0.10,
                    doc.width * 0.26,
                    doc.width * 0.15,
                    doc.width * 0.15,
                    doc.width * 0.16,
                ]
            
            table = Table(items_data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.15, 0.17, 0.46)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.95, 1)),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
            ]))
            elements.append(table)
            
            doc.build(
                elements,
                onFirstPage=self._build_footer,
                onLaterPages=self._build_footer,
            )
            
            logger.info(f"✅ PDF دفتر کل ذخیره شد: {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"❌ خطا در PDF دفتر کل: {e}", exc_info=True)
            return False
    
    # ============================================================
    # HTML برای چاپ فیزیکی
    # ============================================================
    
    def generate_voucher_html(self, voucher: dict, items: list) -> str:
        """تولید HTML سند برای چاپ فیزیکی"""
        company_name = self.company_info.get('company_name', '')
        company_economic = self.company_info.get('company_economic', '')
        company_phone = self.company_info.get('company_phone', '')
        company_address = self.company_info.get('company_address', '')
        
        total_debit = sum(float(it.get('debit', 0) or 0) for it in items)
        total_credit = sum(float(it.get('credit', 0) or 0) for it in items)
        
        html = f"""
        <html>
        <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Tahoma, sans-serif;
                direction: rtl;
                padding: 15px;
                color: #2c3e50;
                font-size: 11pt;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #273c75;
                padding-bottom: 10px;
                margin-bottom: 15px;
            }}
            .company-name {{
                font-size: 18pt;
                font-weight: bold;
                color: #273c75;
            }}
            .company-info {{
                font-size: 10pt;
                color: #555;
                margin-top: 5px;
            }}
            .title {{
                font-size: 15pt;
                font-weight: bold;
                margin-top: 10px;
            }}
            .info {{
                margin-bottom: 15px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 5px;
            }}
            .info table {{ width: 100%; }}
            .info td {{ padding: 4px 5px; font-size: 11pt; }}
            table.items {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            table.items th {{
                background-color: #273c75;
                color: white;
                padding: 8px;
                text-align: center;
                font-size: 11pt;
            }}
            table.items td {{
                border: 1px solid #ddd;
                padding: 7px;
                text-align: center;
                font-size: 11pt;
            }}
            .totals {{
                margin-top: 15px;
                padding: 10px;
                background: #f0f0f0;
                border-radius: 5px;
            }}
            .footer {{
                margin-top: 30px;
                text-align: center;
                font-size: 9pt;
                color: #999;
                border-top: 1px solid #ddd;
                padding-top: 10px;
            }}
            .status-ok {{
                color: #27ae60;
                font-weight: bold;
                font-size: 13pt;
            }}
            .status-fail {{
                color: #e74c3c;
                font-weight: bold;
                font-size: 13pt;
            }}
            .signs {{
                width: 100%;
                margin-top: 40px;
            }}
            .signs td {{
                text-align: center;
                padding: 5px;
                font-size: 11pt;
            }}
        </style>
        </head>
        <body>
            <div class="header">
                <div class="company-name">{company_name}</div>
                <div class="company-info">
                    {f'کد اقتصادی: {company_economic} | ' if company_economic else ''}
                    {f'تلفن: {company_phone}' if company_phone else ''}
                    {f'<br>آدرس: {company_address}' if company_address else ''}
                </div>
                <div class="title">سند حسابداری</div>
                <div>شماره: {voucher.get('voucher_no', '')}</div>
            </div>
            
            <div class="info">
                <table>
                    <tr>
                        <td><b>تاریخ:</b> {voucher.get('date', '')}</td>
                        <td><b>نوع:</b> {voucher.get('type', 'عادی')}</td>
                    </tr>
                    <tr>
                        <td colspan="2"><b>شرح:</b> {voucher.get('description', '')}</td>
                    </tr>
                </table>
            </div>
            
            <table class="items">
                <thead>
                    <tr>
                        <th>ردیف</th>
                        <th>کد حساب</th>
                        <th>نام حساب</th>
                        <th>شرح</th>
                        <th>بدهکار</th>
                        <th>بستانکار</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for i, item in enumerate(items, 1):
            debit = float(item.get('debit', 0) or 0)
            credit = float(item.get('credit', 0) or 0)
            html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{item.get('account_code', '')}</td>
                    <td>{item.get('account_name', '')}</td>
                    <td>{item.get('description', '') or ''}</td>
                    <td>{f"{debit:,.0f}" if debit else "-"}</td>
                    <td>{f"{credit:,.0f}" if credit else "-"}</td>
                </tr>
            """
        
        html += f"""
                </tbody>
                <tfoot>
                    <tr style="background: #e8f5e9; font-weight: bold; font-size: 12pt;">
                        <td colspan="4">جمع کل</td>
                        <td>{total_debit:,.0f}</td>
                        <td>{total_credit:,.0f}</td>
                    </tr>
                </tfoot>
            </table>
            
            <div class="totals">
                <p><b>جمع بدهکار:</b> {total_debit:,.0f} ریال</p>
                <p><b>جمع بستانکار:</b> {total_credit:,.0f} ریال</p>
        """
        
        diff = abs(total_debit - total_credit)
        if diff < 1:
            html += f'<p class="status-ok">✅ سند موازنه است</p>'
        else:
            html += f'<p class="status-fail">⚠️ عدم موازنه: {diff:,.0f} ریال</p>'
        
        html += f"""
            </div>
            
            <table class="signs">
                <tr>
                    <td>تهیه‌کننده</td>
                    <td>تاییدکننده</td>
                    <td>مدیر مالی</td>
                </tr>
                <tr>
                    <td><br><br><br></td>
                    <td><br><br><br></td>
                    <td><br><br><br></td>
                </tr>
            </table>
            
            <div class="footer">
                <p>تاریخ چاپ: {datetime.now().strftime('%Y/%m/%d %H:%M')}</p>
                <p>ImanAccount - حسابداری هوشمند</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def generate_table_html(self, title: str, subtitle: str, headers: list,
                           rows: list, totals: list = None) -> str:
        """تولید HTML جدول عمومی برای چاپ"""
        company_name = self.company_info.get('company_name', '')
        company_economic = self.company_info.get('company_economic', '')
        company_phone = self.company_info.get('company_phone', '')
        company_address = self.company_info.get('company_address', '')
        
        html = f"""
        <html>
        <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Tahoma, sans-serif;
                direction: rtl;
                padding: 15px;
                color: #2c3e50;
                font-size: 10pt;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #273c75;
                padding-bottom: 10px;
                margin-bottom: 15px;
            }}
            .company-name {{
                font-size: 17pt;
                font-weight: bold;
                color: #273c75;
            }}
            .company-info {{
                font-size: 10pt;
                color: #555;
                margin-top: 5px;
            }}
            .title {{
                font-size: 15pt;
                font-weight: bold;
                margin-top: 10px;
            }}
            .subtitle {{
                font-size: 12pt;
                color: #666;
                margin-top: 5px;
            }}
            table.items {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            table.items th {{
                background-color: #273c75;
                color: white;
                padding: 7px;
                text-align: center;
                font-size: 10pt;
            }}
            table.items td {{
                border: 1px solid #ddd;
                padding: 6px;
                text-align: center;
                font-size: 10pt;
            }}
            table.items tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            .totals-row {{
                background-color: #e8f5e9 !important;
                font-weight: bold;
                font-size: 11pt;
            }}
            .footer {{
                margin-top: 30px;
                text-align: center;
                font-size: 9pt;
                color: #999;
                border-top: 1px solid #ddd;
                padding-top: 10px;
            }}
        </style>
        </head>
        <body>
            <div class="header">
                <div class="company-name">{company_name}</div>
                <div class="company-info">
                    {f'کد اقتصادی: {company_economic} | ' if company_economic else ''}
                    {f'تلفن: {company_phone}' if company_phone else ''}
                    {f'<br>آدرس: {company_address}' if company_address else ''}
                </div>
                <div class="title">{title}</div>
                {f'<div class="subtitle">{subtitle}</div>' if subtitle else ''}
            </div>
            
            <table class="items">
                <thead>
                    <tr>
        """
        
        for h in headers:
            html += f"<th>{h}</th>"
        
        html += """
                    </tr>
                </thead>
                <tbody>
        """
        
        for row in rows:
            html += "<tr>"
            for cell in row:
                html += f"<td>{cell}</td>"
            html += "</tr>"
        
        html += """
                </tbody>
        """
        
        if totals:
            html += '<tfoot><tr class="totals-row">'
            for cell in totals:
                html += f"<td>{cell}</td>"
            html += "</tr></tfoot>"
        
        html += f"""
            </table>
            
            <div class="footer">
                <p>تاریخ چاپ: {datetime.now().strftime('%Y/%m/%d %H:%M')}</p>
                <p>ImanAccount - حسابداری هوشمند</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    # ============================================================
    # چاپ فیزیکی — نسخه اصلاح‌شده با اندازه صحیح
    # ============================================================
    
    @staticmethod
    def print_html(html_content: str, parent=None):
        """
        چاپ فیزیکی HTML با پیش‌نمایش
        ✅ نسخه اصلاح‌شده: اندازه صحیح با ScreenResolution
        """
        try:
            # ✅ استفاده از ScreenResolution برای اندازه صحیح
            printer = QPrinter(QPrinter.ScreenResolution)
            printer.setPageSize(QPrinter.A4)
            printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)            
            preview = QPrintPreviewDialog(printer, parent)
            preview.resize(1000, 750)
            
            def _paint(p):
                doc = QTextDocument()
                
                # ✅ مهم: paintDevice رو ست کن
                doc.documentLayout().setPaintDevice(p)
                
                doc.setHtml(html_content)
                
                # ✅ اندازه صفحه رو با QSizeF ست کن
                rect = p.pageRect(QPrinter.DevicePixel)
                size = QSizeF(rect.width(), rect.height())
                doc.setPageSize(size)
                
                doc.print_(p)
            
            preview.paintRequested.connect(_paint)
            preview.exec_()
            
        except Exception as e:
            logger.error(f"خطا در چاپ: {e}", exc_info=True)
            if parent:
                QMessageBox.warning(parent, "خطا", f"❌ خطا در چاپ: {str(e)}")
    
    # ============================================================
    # دیالوگ ذخیره PDF
    # ============================================================
    
    @staticmethod
    def ask_save_path(parent, default_name: str) -> str:
        """دیالوگ انتخاب مسیر ذخیره PDF"""
        file_path, _ = QFileDialog.getSaveFileName(
            parent,
            "ذخیره PDF",
            default_name,
            "PDF Files (*.pdf)"
        )
        return file_path


# ============================================================
# ========== Singleton ==========
# ============================================================

_generator_instance = None


def get_pdf_generator(company_info: dict = None) -> AccountingPDFGenerator:
    """دریافت نمونه PDF Generator"""
    global _generator_instance
    if _generator_instance is None or company_info:
        _generator_instance = AccountingPDFGenerator(company_info)
    return _generator_instance


# ============================================================
# ========== تست ==========
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    gen = AccountingPDFGenerator({
        'company_name': 'شرکت تست',
        'company_economic': '1234567890',
        'company_phone': '021-12345678',
        'company_address': 'تهران، خیابان تست',
    })
    
    voucher = {
        'voucher_no': 1,
        'date': '1404/01/15',
        'description': 'سند تست',
        'type': 'عادی',
    }
    
    items = [
        {'account_code': '1101', 'account_name': 'صندوق',
         'description': 'دریافت نقدی', 'debit': 1000000, 'credit': 0},
        {'account_code': '4101', 'account_name': 'فروش کالا',
         'description': 'فروش', 'debit': 0, 'credit': 1000000},
    ]
    
    gen.generate_voucher_pdf(voucher, items, "test_voucher.pdf")
    print("✅ تست انجام شد")
