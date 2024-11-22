Program Overview:

  This Flask program allows you to replace product codes with clickable product links in PDF files, such as technical drawings. Here's how it works:

Manufacturer Information:

  The program extracts the manufacturer's name from the folder name that contains your PDF files.
  It also reads the product codes listed within those PDF files.

CSV File Setup:

  You need to provide a CSV file with the following information:
  
    1. Manufacturer Name: Enter the name of the manufacturer in the "name" column.
    
    2. Manufacturer Codes: Enter the product codes provided by the manufacturer (as shown on their technical drawings) in the "Symbol" column.
    
    3. Your Store Codes: Enter the corresponding product codes used in your store in the "Symbol_1" column.
    
Adding Links:

  The program uses the CSV file to match the manufacturer’s codes with your store’s codes.
  It then replaces the product codes in the PDF with links to the corresponding products in your store.

How to run:
  1. Open CMD.
  2. Select the directory of the folder with the program.
  3. Run "python app6.py" command.
  4. Open your browser and put your IPv4 with ":5000" or http://127.0.0.1:5000/

Steps to Use the Program:
  
  1. Replace placeholders in the code with proper paths.

  2. Prepare the CSV File
     
    1. Create a CSV file with three columns: name, Symbol, and Symbol_1.
    2. Fill in the manufacturer’s name, their product codes, and your store’s product codes accordingly.

  3. Organize Your Files
     
    For One Manufacturer:

      1. Create a folder named after the manufacturer and place all relevant PDF files inside.
      2. Enter the path to this folder in the program.
      
    For Multiple Manufacturers:

      1. Create a main folder.
      2. Inside the main folder, create separate subfolders for each manufacturer, naming each subfolder with the respective manufacturer's name.
      3. Place the corresponding PDF files inside each manufacturer’s subfolder.
      4. Enter the path to the main folder in the program. The program will then process each manufacturer's subfolder automatically.

  4. Run the Program
     
    Put the CSV file path into the code.
    Put the path of your PDF folder into the textbox.
    Put in the base link, the code will get added at the end of the link: https://yourdomain.com/pdf/{Your_Code}.
    The program will automatically replace the product codes in the PDFs with the appropriate links.

This tool streamlines the process of linking products in your technical documents, making it easier for users to access product information directly from the PDFs.
