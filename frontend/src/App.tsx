import React, { useState } from "react";

const App: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [response, setResponse] = useState<string>("");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      alert("Please select a file to upload!");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://192.168.5.1:5555/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setResponse(JSON.stringify(data, null, 2));
    } catch (err) {
      console.error(err);
      alert("An error occurred while uploading the file.");
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-300">
      <h1 className="text-3xl font-bold mb-6">Upload a Python Script</h1>
      <form
        className="flex flex-col items-center space-y-4 bg-white p-6 rounded-lg shadow-lg"
        onSubmit={handleSubmit}
      >
        <input
          type="file"
          onChange={handleFileChange}
          accept=".py"
          className="border border-gray-300 p-2 rounded-md"
        />
        <button
          type="submit"
          className="bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600"
        >
          Submit
        </button>
      </form>
      {response && (
        <div className="mt-6 p-4 bg-gray-200 rounded-lg shadow-md w-96">
          <h2 className="text-lg font-bold mb-2">Server Response:</h2>
          <pre className="text-sm whitespace-pre-wrap">{response}</pre>
        </div>
      )}
    </div>
  );
};

export default App;
