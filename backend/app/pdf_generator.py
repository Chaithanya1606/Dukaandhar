import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

def generate_bill_pdf(bill_data: dict, store_profile: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'StoreTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a")
    )
    
    sub_title_style = ParagraphStyle(
        'StoreSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569")
    )

    badge_style = ParagraphStyle(
        'Badge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1e3a8a")
    )

    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155")
    )

    val_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f172a")
    )

    right_val_style = ParagraphStyle(
        'RightValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#0f172a")
    )

    right_bold_style = ParagraphStyle(
        'RightBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#0f172a")
    )

    elements = []

    # 1. Store Header
    store_name = store_profile.get("store_name", "CEMENT RESALE STORE")
    owner_name = store_profile.get("owner_name", "")
    phone = store_profile.get("phone", "")
    alt_phone = store_profile.get("alt_phone", "")
    address = store_profile.get("address", "")
    gstin = store_profile.get("gstin", "")
    upi_id = store_profile.get("upi_id", "")

    elements.append(Paragraph(store_name.upper(), title_style))
    contact_info = f"Address: {address}"
    phone_info = f"Phone: {phone}" + (f" / {alt_phone}" if alt_phone else "")
    if gstin:
        phone_info += f" | GSTIN: {gstin}"
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(contact_info, sub_title_style))
    elements.append(Paragraph(phone_info, sub_title_style))
    elements.append(Spacer(1, 3 * mm))
    
    # Divider & Title
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=4))
    elements.append(Paragraph("TAX INVOICE / CASH MEMO", badge_style))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceBefore=3, spaceAfter=5))

    # 2. Invoice & Customer Meta Table
    bill_number = bill_data.get("bill_number", "BILL-0001")
    bill_date = bill_data.get("date", datetime.now().strftime("%Y-%m-%d %H:%M"))
    vehicle_no = bill_data.get("vehicle_no") or "N/A"
    delivery_site = bill_data.get("delivery_site") or "Direct Store Pickup"
    cust_name = bill_data.get("customer_name", "Cash Customer")
    cust_phone = bill_data.get("customer_phone") or "N/A"
    payment_mode = bill_data.get("payment_mode", "Cash")

    meta_data = [
        [
            Paragraph("<b>Invoice No:</b> " + bill_number, val_style),
            Paragraph("<b>Customer Name:</b> " + cust_name, val_style)
        ],
        [
            Paragraph("<b>Date:</b> " + bill_date, val_style),
            Paragraph("<b>Mobile:</b> " + cust_phone, val_style)
        ],
        [
            Paragraph("<b>Vehicle/Lorry No:</b> " + vehicle_no, val_style),
            Paragraph("<b>Delivery Site:</b> " + delivery_site, val_style)
        ],
        [
            Paragraph("<b>Payment Mode:</b> " + payment_mode, val_style),
            Paragraph("<b>State Code:</b> 36 (Telangana)", val_style)
        ]
    ]

    meta_table = Table(meta_data, colWidths=[90 * mm, 96 * mm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 4 * mm))

    # 3. Itemized Products Table
    items_header = [
        Paragraph("<b>#</b>", label_style),
        Paragraph("<b>Description / Cement Brand</b>", label_style),
        Paragraph("<b>HSN</b>", label_style),
        Paragraph("<b>Bags</b>", right_bold_style),
        Paragraph("<b>Weight (MT)</b>", right_bold_style),
        Paragraph("<b>Rate (Rs.)</b>", right_bold_style),
        Paragraph("<b>Total (Rs.)</b>", right_bold_style),
    ]

    items_rows = [items_header]
    items = bill_data.get("items", [])
    for idx, item in enumerate(items, 1):
        brand_desc = f"<b>{item.get('brand')}</b><br/><font size=7 color='#64748b'>{item.get('grade')}</font>"
        items_rows.append([
            Paragraph(str(idx), val_style),
            Paragraph(brand_desc, val_style),
            Paragraph(str(item.get("hsn_code", "2523")), val_style),
            Paragraph(str(item.get("quantity_bags")), right_val_style),
            Paragraph(f"{item.get('weight_tonnes', 0.0):.2f}", right_val_style),
            Paragraph(f"{item.get('unit_price', 0.0):,.2f}", right_val_style),
            Paragraph(f"{item.get('total_price', 0.0):,.2f}", right_val_style),
        ])

    items_table = Table(items_rows, colWidths=[8*mm, 68*mm, 16*mm, 20*mm, 24*mm, 24*mm, 26*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
        ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor("#94a3b8")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 3 * mm))

    # 4. Summary & Calculations Table
    subtotal = bill_data.get("subtotal", 0.0)
    transport = bill_data.get("transport_charges", 0.0)
    hamali = bill_data.get("hamali_charges", 0.0)
    discount = bill_data.get("discount", 0.0)
    gst_rate = bill_data.get("gst_rate", 0.0)
    gst_amount = bill_data.get("gst_amount", 0.0)
    grand_total = bill_data.get("grand_total", 0.0)
    amount_paid = bill_data.get("amount_paid", 0.0)
    due_amount = bill_data.get("due_amount", 0.0)
    total_bags = bill_data.get("total_bags", 0)
    total_tonnes = bill_data.get("total_tonnes", 0.0)

    calc_rows = [
        [Paragraph(f"<b>Total Quantity:</b> {total_bags} Bags ({total_tonnes:.2f} Metric Tonnes)", val_style), Paragraph("Material Subtotal:", label_style), Paragraph(f"Rs. {subtotal:,.2f}", right_bold_style)],
    ]
    if transport > 0:
        calc_rows.append([Paragraph("", val_style), Paragraph("Lorry Transport / Freight:", val_style), Paragraph(f"+ Rs. {transport:,.2f}", right_val_style)])
    if hamali > 0:
        calc_rows.append([Paragraph("", val_style), Paragraph("Hamali / Unloading Charges:", val_style), Paragraph(f"+ Rs. {hamali:,.2f}", right_val_style)])
    if discount > 0:
        calc_rows.append([Paragraph("", val_style), Paragraph("Discount Allowed:", val_style), Paragraph(f"- Rs. {discount:,.2f}", right_val_style)])
    if gst_amount > 0:
        calc_rows.append([Paragraph("", val_style), Paragraph(f"GST ({gst_rate}%):", val_style), Paragraph(f"+ Rs. {gst_amount:,.2f}", right_val_style)])

    grand_total_style = ParagraphStyle(
        'GrandTotalVal',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#1e3a8a")
    )
    grand_total_lbl = ParagraphStyle(
        'GrandTotalLbl',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=colors.HexColor("#1e3a8a")
    )

    calc_rows.append([
        Paragraph(f"<b>Amount in Words:</b><br/>{number_to_indian_currency_words(grand_total)}", ParagraphStyle('Words', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor("#334155"))),
        Paragraph("GRAND TOTAL:", grand_total_lbl),
        Paragraph(f"Rs. {grand_total:,.2f}", grand_total_style)
    ])

    calc_rows.append([
        Paragraph(f"<b>UPI for Payment:</b> {upi_id}" if upi_id else "", val_style),
        Paragraph("Amount Paid:", label_style),
        Paragraph(f"Rs. {amount_paid:,.2f}", right_val_style)
    ])

    if due_amount > 0:
        calc_rows.append([
            Paragraph("<b>Payment Status:</b> <font color='#dc2626'><b>BALANCE DUE</b></font>", val_style),
            Paragraph("<font color='#dc2626'><b>Balance Due (Udhar):</b></font>", label_style),
            Paragraph(f"<font color='#dc2626'><b>Rs. {due_amount:,.2f}</b></font>", right_bold_style)
        ])
    else:
        calc_rows.append([
            Paragraph("<b>Payment Status:</b> <font color='#16a34a'><b>PAID IN FULL</b></font>", val_style),
            Paragraph("Balance Due:", label_style),
            Paragraph("Rs. 0.00", right_val_style)
        ])

    calc_table = Table(calc_rows, colWidths=[96 * mm, 50 * mm, 40 * mm])
    calc_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
        ('INNERGRID', (1,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('BACKGROUND', (1,-3), (-1,-3), colors.HexColor("#dbeafe")), # Grand total row highlight
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(calc_table)
    elements.append(Spacer(1, 6 * mm))

    # 5. Terms & Signatures
    footer_note = store_profile.get("bill_footer_note", "Thank you for your business! Goods once sold will not be taken back.")
    sign_data = [
        [
            Paragraph(f"<b>Terms & Conditions:</b><br/><font size=7 color='#64748b'>1. {footer_note}<br/>2. Discrepancy if any must be informed within 24 hours.<br/>3. Subject to local jurisdiction.</font>", val_style),
            Paragraph(f"For <b>{store_name}</b><br/><br/><br/><br/><b>Authorized Signatory</b>", ParagraphStyle('Sign', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, leading=11))
        ]
    ]
    sign_table = Table(sign_data, colWidths=[120 * mm, 66 * mm])
    sign_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    elements.append(sign_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

def number_to_indian_currency_words(num: float) -> str:
    """Helper to format number into Indian currency words (Lakhs, Crores)"""
    num = round(num, 2)
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
             "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def convert_below_thousand(n):
        res = []
        if n >= 100:
            res.append(units[n // 100] + " Hundred")
            n %= 100
        if 0 < n < 20:
            res.append(units[n])
        elif n >= 20:
            res.append(tens[n // 10])
            if n % 10:
                res.append(units[n % 10])
        return " ".join(res)

    int_part = int(num)
    paise = int(round((num - int_part) * 100))

    if int_part == 0:
        words = "Zero Rupees"
    else:
        parts = []
        crores = int_part // 10000000
        int_part %= 10000000
        lakhs = int_part // 100000
        int_part %= 100000
        thousands = int_part // 1000
        int_part %= 1000
        hundreds_and_below = int_part

        if crores > 0:
            parts.append(convert_below_thousand(crores) + " Crore")
        if lakhs > 0:
            parts.append(convert_below_thousand(lakhs) + " Lakh")
        if thousands > 0:
            parts.append(convert_below_thousand(thousands) + " Thousand")
        if hundreds_and_below > 0:
            parts.append(convert_below_thousand(hundreds_and_below))

        words = " ".join(parts) + " Rupees"

    if paise > 0:
        words += f" and {convert_below_thousand(paise)} Paise"
    return words + " Only"
