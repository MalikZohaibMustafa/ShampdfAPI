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
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.utils import ImageReader

from bidi.algorithm import get_display
import arabic_reshaper
from googletrans import Translator, LANGUAGES
from google.cloud import translate_v2 as translate



page_width, page_height = letter

# def translate_text(text, target_language):
#     client = translate.Client('AIzaSyCUKXdiIMLeUYQoaXlJhu4q8Flpc-3k_U0')
#     result = client.translate(text, target_language=target_language)
#     return result['translatedText']

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


@app.route('/generate-pdf/<int:quotation_id>', methods=['POST'])
def generate_pdf(quotation_id):
    if not quotation_id:
        return jsonify({"error": "Quotation not found"}), 404

    data = request.json
    
    # Generate only English PDF
    english_pdf_path = create_pdf(quotation_id, data, 'english')

    # Send the English PDF file
    return send_file(english_pdf_path, as_attachment=False)


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
    pdf_path = f"quotation_{language}.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elements = []
    overall_total = 0
    background_image_path = 'bg.jpeg'  # Update with the path to your image
    background_image = ImageReader(background_image_path)

    # Define the canvas method to add the background image
    def create_page(canvas, doc):
        canvas.drawImage(background_image, x=0, y=0, width=page_width, height=page_height)
        canvas.saveState()
        # Other content to be drawn on the page should go here
        canvas.restoreState()
    doc.build(elements, onFirstPage=create_page, onLaterPages=create_page)

    # image_left = Image('LeftLogo.PNG', 1.25*inch, 1*inch)
    # image_right = Image('RightLogo.PNG', 1.75*inch, 0.8*inch)
    # image_table = Table([[image_left, '', image_right]], colWidths=[2*inch, 3*inch, 1*inch])
    # elements.append(image_table)

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

