import { useRef } from "react";

const backendUrl = import.meta.env.VITE_BACKEND_URL;

export default function UploadButton() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const handleFileClick = () => fileInputRef.current?.click();
  const handleFolderClick = () => folderInputRef.current?.click();

  const handleFiles = async (fileList: FileList | null, isFolder: boolean) => {
    if (!fileList || fileList.length === 0) return;

    const formData = new FormData();
    Array.from(fileList).forEach((file) => {
      formData.append("files", file, file.webkitRelativePath || file.name);
    });

    const endpoint = isFolder
      ? `${backendUrl}/upload-folder`
      : `${backendUrl}/upload`;

    const res = await fetch(endpoint, {
      method: "POST",
      body: formData,
      credentials: "include",
    });

    alert(res.ok ? "Upload successful" : "Upload failed");
  };

  return (
    <>
      <div className="flex gap-4 mb-2">
        <button
          onClick={handleFileClick}
          className="px-4 py-2 bg-blue-600 text-white rounded"
        >
          Upload Files
        </button>
        <button
          onClick={handleFolderClick}
          className="px-4 py-2 bg-green-600 text-white rounded"
        >
          Upload Folder
        </button>
      </div>

      <input
        type="file"
        ref={fileInputRef}
        onChange={(e) => handleFiles(e.target.files, false)}
        className="hidden"
        multiple
      />

      <input
        type="file"
        ref={folderInputRef}
        onChange={(e) => handleFiles(e.target.files, true)}
        className="hidden"
        // @ts-expect-error webkitdirectory is not supported in all browsers
        webkitdirectory=""
        directory=""
      />
    </>
  );
}
