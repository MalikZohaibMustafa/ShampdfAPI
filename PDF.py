import os
from bidi.algorithm import get_display
import arabic_reshaper
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS

from reportlab.lib import colors
from reportlab.pdfgen import canvas
import zipfile

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import datetime
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.utils import ImageReader

from bidi.algorithm import get_display
import arabic_reshaper
from googletrans import Translator, LANGUAGES
from google.cloud import translate_v2 as translate

from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

amiri_regular_path = 'Amiri-Regular.ttf'
amiri_bold__path = 'Amiri-Bold.ttf'
amiri_italic_path= 'Amiri-Italic.ttf'
amiri_bold_italic_path = 'Amiri-BoldItalic.ttf'

pdfmetrics.registerFont(TTFont('Amiri', amiri_regular_path))
pdfmetrics.registerFont(TTFont('Amiri-Bold', amiri_bold__path))
pdfmetrics.registerFont(TTFont('Amiri-Italic', amiri_italic_path))
pdfmetrics.registerFont(TTFont('Amiri-BoldItalic', amiri_bold_italic_path))
page_width, page_height = letter

app = Flask(__name__)
CORS(app)

def translate_text(text, dest_language):
    translator = Translator()
    translation = translator.translate(text, dest=dest_language)
    return translation.text

def reshape_arabic(text):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

@app.route('/generate-pdf/<int:quotation_id>/<language>', methods=['POST'])
def generate_pdf(quotation_id, language):
    if not quotation_id:
        return jsonify({"error": "Quotation not found"}), 404

    data = request.json
    
    # Check the language and generate corresponding PDF
    if language == 'english':
        pdf_path = create_pdf(quotation_id, data, 'english')
    elif language == 'arabic':
        pdf_path = create_pdf(quotation_id, data, 'arabic')
    else:
        return jsonify({"error": "Invalid language"}), 400

    return send_file(pdf_path, as_attachment=True)

# @app.route('/generate-pdf', methods=['POST'])
# def generate_pdf():
#     data = request.json
    
#     # Generate English and Arabic PDFs
#     english_pdf_path = create_pdf(data, 'english')
#     arabic_data = translate_data_to_arabic(data)
#     # arabic_data = translate_text(data)

#     arabic_pdf_path = create_pdf(arabic_data, 'arabic')

#     # Zip the files
#     zip_path = "quotation_files.zip"
#     with zipfile.ZipFile(zip_path, 'w') as zipf:
#         zipf.write(english_pdf_path, os.path.basename(english_pdf_path))
#         zipf.write(arabic_pdf_path, os.path.basename(arabic_pdf_path))

#     # Send the zip file
#     return send_file(zip_path, as_attachment=True)

def translate_data_to_arabic(data):
    # Assuming the data is a dictionary with text values
    arabic_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            arabic_data[key] = translate_text(value, 'ar')
        else:
            arabic_data[key] = value
    return arabic_data



def create_pdf(quotation_id,data, language):
    if language == 'arabic':
        styles = getSampleStyleSheet()
        pdf_path = f"Arabic_quotation_{language}.pdf"
        paragraph_right_style = ParagraphStyle('ArabicStyle', fontName='Amiri', alignment=TA_RIGHT)
        paragraph_left_style = ParagraphStyle('ArabicStyle', fontName='Amiri', alignment=TA_LEFT)
        paragraph_center_style = ParagraphStyle('ArabicStyle', fontName='Amiri', alignment=TA_CENTER)
        arabic_bold_style_Right = ParagraphStyle(
            'ArabicBold',
            parent=styles['Normal'],
            fontName='Amiri-Bold',
            fontSize=12,  # Set the desired font size
            alignment=TA_RIGHT
        )
        arabic_bold_style_Left = ParagraphStyle(
            'ArabicBold',
            parent=styles['Normal'],
            fontName='Amiri-Bold',
            fontSize=12,  # Set the desired font size
            alignment=TA_LEFT
        )
        arabic_bold_style_Center = ParagraphStyle(
            'ArabicBold',
            parent=styles['Normal'],
            fontName='Amiri-Bold',
            fontSize=12,  # Set the desired font size
            alignment=TA_CENTER
        )
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        elements = []
        overall_total = 0
        background_image_path = 'bg.jpeg'  
        background_image = ImageReader(background_image_path)
        def create_page(canvas, doc):
                    canvas.drawImage(background_image, x=0, y=0, width=page_width, height=page_height)
                    canvas.saveState()
                    canvas.restoreState()
        doc.build(elements, onFirstPage=create_page, onLaterPages=create_page)

        elements.append(Spacer(1, 0.25*inch))
        styles = getSampleStyleSheet()
        bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold')

        elements.append(Image('CenterImage.PNG', 1.2*inch, 0.3*inch, hAlign=TA_CENTER))
        elements.append(Spacer(1, 0.25*inch))

        elements.append(Paragraph(reshape_arabic(f"عرض أسعار رقم العرض : {quotation_id} / 2023"),arabic_bold_style_Center))
        elements.append(Spacer(1, 0.25*inch))

        
        elements.append(Paragraph(data.get('quoteDate', '') + reshape_arabic(": تاريخ "),paragraph_left_style))
        elements.append(Spacer(2, 0.25*inch))
        elements.append(Paragraph(data.get('customer', '').get('name','') + reshape_arabic(" عزيزي: "),arabic_bold_style_Right))
        elements.append(Spacer(2, 0.25*inch))        
        elements.append(Paragraph(reshape_arabic(f"السالم عليكم ورحمة ٱللَّٰه وبركاته"),arabic_bold_style_Right))
        elements.append(Spacer(2, 0.25*inch))        
        elements.append(Paragraph(reshape_arabic(f"يسرنا أن نتقدم اليكم بعرض األسعار التالي :"),arabic_bold_style_Right))
        elements.append(Spacer(3, 0.25*inch))        

        arabic_table_headers = [
            reshape_arabic('السعر االجمالي \ ريال'), #Total Price/SAR
            reshape_arabic('السعر المخفض/ريال'), #Discounted Price/SAR
            reshape_arabic('العدد'), #Quantity
            reshape_arabic('السعر االفرادي \ ريال'), #Price/SAR
            reshape_arabic('القياس - سنوات'), #Size
            reshape_arabic('المرحلة') #Product Name 
        ]
        table_data = [
            [reshape_arabic('إقتباس الراجحي 2023') ],
            arabic_table_headers
            ]
        
        for product in data['productList']:
            product_name = reshape_arabic(product['product']['arabicProductName'])
            base_price = float(product['product']['basePrice'])

            for size in product['selectedSizes']:
                base_price = float(product['product']['basePrice'])
                quantity = float(product['quantity'])
                individual_discount = float(product.get('discount', 0)) / 100

                discounted_price = base_price * (1 - individual_discount)
                total_price = discounted_price * quantity
                overall_total += total_price

                row = [
                    "{:.2f}".format(total_price),
                    "{:.2f}".format(discounted_price),
                    str(quantity),
                    "{:.2f}".format(base_price),
                    size['size'],
                    product_name,
                ]
                table_data.append(row)
                product_name = ""  # Clear pro
        light_sky_blue = colors.Color(0.53, 0.81, 0.98)  # Adjust the RGB values as needed

        table_style = TableStyle([
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONT', (0, 0), (-1, 0), 'Amiri-Bold'),
            ('SPAN', (0, 0), (-1, 0)),  # Span for first row

            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTSIZE', (0, 0), (-1, 0), 12),


            ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
            ('FONT', (0, 1), (-1, 1), 'Amiri-Bold'),
            ('BACKGROUND', (0, 1), (-1, 1), light_sky_blue),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.black),
            ('FONTSIZE', (0, 1), (-1, 1), 10),

            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONT', (0, 0), (-1, -1), 'Amiri'),  # Apply Amiri font
            ('FONTSIZE', (0, 0), (-1, -1), 10)
        ])

        elements.append(Spacer(5, 0.25*inch))
        # Calculate subtotal if not already calculated
        subtotal = sum(float(row[0].replace(',', '').replace('ريال', '').strip()) for row in table_data[2:])

      # Add subtotal row with subtotal in the first cell
        subtotal_row = [f"{subtotal:.2f}"] + [""] * (len(arabic_table_headers) - 1)
        table_data.append(subtotal_row)

        # Update the table style to include the subtotal row
        table_style.add('SPAN', (0, -1), (-1, -1))  # Span from the first cell to the last cell in the subtotal row
        table_style.add('ALIGN', (0, -1), (0, -1), 'LEFT')  # Left align the first cell in the subtotal row
        table_style.add('FONT', (0, -1), (-1, -1), 'Amiri-Bold')  # Bold font for subtotal row

        # Create and add the table to the document
        arabic_table = Table(table_data, style=table_style)
        elements.append(arabic_table)
        elements.append(Spacer(5, 0.25*inch))
        elements.append(Paragraph(reshape_arabic(f"نأمل أن يتجاوز اقتراحنا توقعاتك، ونتطلع إلى العمل معه أنت."),arabic_bold_style_Right))
        elements.append(Spacer(3, 0.25*inch))

        elements.append(Paragraph(reshape_arabic(f"زي الشام للأناقة ."),arabic_bold_style_Right))

        doc.build(elements)
    
        return pdf_path

    else:
        pdf_path = f"quotation_{language}.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        elements = []
        overall_total = 0
        background_image_path = 'bg.jpeg'
        background_image = ImageReader(background_image_path)

        def create_page(canvas, doc):
            canvas.drawImage(background_image, x=0, y=0, width=page_width, height=page_height)
            canvas.saveState()
            # Other content to be drawn on the page should go here
            canvas.restoreState()
        doc.build(elements, onFirstPage=create_page, onLaterPages=create_page)

        elements.append(Spacer(1, 0.25*inch))

        # Add another image in the center with a smaller size
        elements.append(Image('CenterImage.PNG', 1.2*inch, 0.3*inch, hAlign=TA_CENTER))
        elements.append(Spacer(1, 0.25*inch))

        # Add Quotation ID, Date, Customer Name with specific formatting
        styles = getSampleStyleSheet()
        bold_center_style = ParagraphStyle('BoldCenterStyle', parent=styles['Normal'], fontName='Helvetica-Bold', alignment=TA_CENTER)
        bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold')

        elements.append(Paragraph(f"Quotation number: {quotation_id} / 2023", bold_center_style))
        elements.append(Spacer(1, 0.25*inch))

        elements.append(Paragraph("Date: " + datetime.datetime.now().strftime("%d/%m/%Y"), bold_style))
        elements.append(Paragraph("Dear: " + data['customer']['name'], bold_style))

        elements.append(Paragraph("We are glad to present you with the following quotation:", bold_style))

        elements.append(Spacer(1, 0.25*inch))
    
    # Styles
        styles = getSampleStyleSheet()
        bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold')

        # Table with special first row and bold headings
        table_data = [
            ["AlRajhi Quotation 2023"],  # First row
            ["Product Name", "Size", "Price/SAR", "Quantity", "Discounted Price/SAR", "Total Price/SAR"]  # Headings
        ]
        # Populate table_data with items from data['productList']
        for product in data['productList']:
            product_name = product['product']['productName']
            base_price = float(product['product']['basePrice'])

            for size in product['selectedSizes']:
                base_price = float(product['product']['basePrice'])
                quantity = float(product['quantity'])
                individual_discount = float(product.get('discount', 0)) / 100

                discounted_price = base_price * (1 - individual_discount)
                total_price = discounted_price * quantity
                overall_total += total_price

                row = [
                    product_name,
                    size['size'],
                    "{:.2f}".format(base_price),
                    str(quantity),
                    "{:.2f}".format(discounted_price),
                    "{:.2f}".format(total_price)
                ]
                table_data.append(row)
                product_name = ""  # Clear pro
        # Define table style
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('SPAN', (0, 0), (-1, 0)),  # Span for first row
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),  # Bold for headings
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 2), (-1, -1), 'CENTER')
        ])
        table = Table(table_data, colWidths=[None] * 6, style=table_style)
        elements.append(table)
        # Adding Overall Total Field
        elements.append(Spacer(1, 0.25*inch))
        total_style = ParagraphStyle('TotalStyle', parent=styles['Normal'], fontName='Helvetica-Bold', alignment=TA_RIGHT)
        elements.append(Paragraph(f"Overall Total: SAR {overall_total:.2f}", total_style))


    # Styles
        styles = getSampleStyleSheet()
        bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold')

        # Adding paragraphs in bold
        elements.append(Spacer(1, 0.25*inch))
        elements.append(Paragraph("We hope that our proposal exceeds your expectations, and we look forward to working with you.", bold_style))
        elements.append(Spacer(1, 0.25*inch))
        elements.append(Spacer(1, 0.25*inch))
        elements.append(Paragraph("Sham Elegance Uniform", bold_style))
        if language == 'arabic':
            new_elements = []
            for element in elements:
                if isinstance(element, Paragraph):
                    # Apply reshaping and bidi reordering to Arabic text
                    arabic_text = reshape_arabic(element.text)
                    new_paragraph = Paragraph(arabic_text, element.style)
                    new_elements.append(new_paragraph)
                else:
                    new_elements.append(element)
            elements = new_elements


        # Generate PDF
        doc.build(elements)
    
        return pdf_path

def reshape_arabic(text):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text
if __name__ == '__main__':
    app.run(debug=True)

