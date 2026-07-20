/**
 * CVMI Web Annotator Google Drive Bridge - Multi-Doctor Edition
 * 
 * Instructions:
 * 1. Go to https://script.google.com and replace Code.gs with this exact code.
 * 2. Click Save (Ctrl+S).
 * 3. Click Deploy -> New Deployment.
 * 4. Select type: Web App
 * 5. Execute as: Me (your email)
 * 6. Who has access: Anyone
 * 7. Copy the Web App URL!
 */

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    
    // Extract metadata
    var imagePath = data.image_path || "unknown.jpg";
    var doctorName = data.doctor_name ? sanitizeFolderName(data.doctor_name) : "Unassigned_Doctor";
    var filename = imagePath + "_landmarks.json";
    
    // Add server timestamp
    data.saved_at = new Date().toISOString();
    
    // Target Google Drive Master Folder ID
    var masterFolderId = "163ChCnp0u-LfHR9Sh2XxKNYomvS03QQ3";
    var masterFolder = DriveApp.getFolderById(masterFolderId);
    
    // Locate or create Doctor-specific subfolder
    var subfolders = masterFolder.getFoldersByName(doctorName);
    var doctorFolder;
    if (subfolders.hasNext()) {
      doctorFolder = subfolders.next();
    } else {
      doctorFolder = masterFolder.createFolder(doctorName);
    }
    
    // Save or overwrite annotation file in Doctor subfolder
    var files = doctorFolder.getFilesByName(filename);
    var file;
    if (files.hasNext()) {
      file = files.next();
      file.setContent(JSON.stringify(data, null, 4));
    } else {
      file = doctorFolder.createFile(filename, JSON.stringify(data, null, 4), MimeType.PLAIN_TEXT);
    }
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success", 
      fileId: file.getId(),
      filename: filename,
      doctor: doctorName,
      folderId: doctorFolder.getId()
    })).setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error", 
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function sanitizeFolderName(name) {
  return name.trim().replace(/[\/\\?%*:|"<>]/g, '_');
}

function doOptions(e) {
  return ContentService.createTextOutput("").setMimeType(ContentService.MimeType.JSON);
}
