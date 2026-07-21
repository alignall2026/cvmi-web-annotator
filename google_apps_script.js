/**
 * CVMI Web Annotator Google Drive Bridge - Multi-Doctor Edition (With Sync & Retrieval)
 * 
 * Instructions:
 * 1. Go to https://script.google.com and replace Code.gs with this code.
 * 2. Click Save (Ctrl+S).
 * 3. Click Deploy -> Manage Deployments -> Edit -> New Version -> Deploy!
 */

function doGet(e) {
  try {
    var doctorName = e.parameter.doctor_name ? sanitizeFolderName(e.parameter.doctor_name) : "";
    var imageName = e.parameter.image_name || "";
    
    var masterFolderId = "163ChCnp0u-LfHR9Sh2XxKNYomvS03QQ3";
    var masterFolder = DriveApp.getFolderById(masterFolderId);
    
    if (!doctorName) {
      return ContentService.createTextOutput(JSON.stringify({ status: "error", message: "doctor_name parameter required" }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    var subfolders = masterFolder.getFoldersByName(doctorName);
    if (!subfolders.hasNext()) {
      return ContentService.createTextOutput(JSON.stringify({ status: "success", doctor: doctorName, saved_images: [], landmarks_map: {} }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    var doctorFolder = subfolders.next();
    var files = doctorFolder.getFiles();
    var savedImages = [];
    var landmarksMap = {};
    
    while (files.hasNext()) {
      var file = files.next();
      var fname = file.getName();
      if (fname.indexOf("_landmarks.json") !== -1) {
        var rawImg = fname.replace("_landmarks.json", "");
        savedImages.push(rawImg);
        
        if (imageName && rawImg === imageName) {
          try {
            var content = JSON.parse(file.getBlob().getDataAsString());
            landmarksMap[rawImg] = content.landmarks;
          } catch(err) {}
        }
      }
    }
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      doctor: doctorName,
      saved_images: savedImages,
      landmarks_map: landmarksMap
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

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
