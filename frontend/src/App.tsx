import React, { useState, useEffect, useRef } from "react";
import { io } from "socket.io-client";

const App: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [logs, setLogs] = useState<{ type: string; message: string; }[]>([]);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const terminalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

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

    setIsUploading(true);
    setLogs([]); // Clear logs for new upload

    const formData = new FormData();
    formData.append("file", file);

    try {
      await fetch("http://172.27.69.26:5555/upload", {
        method: "POST",
        body: formData,
      });
    } catch (err) {
      console.error(err);
      alert("An error occurred while uploading the file.");
    } finally {
      setIsUploading(false);
    }
  };

  useEffect(() => {
    const socket = io("http://172.27.69.26:5555");

    let roomId: string | null = null;

    socket.on("connect", () => {
      console.log("WebSocket connected:", socket.id);
    });

    socket.on("room", (data: { room_id: string }) => {
      roomId = data.room_id;
      socket.emit("join", { room_id: roomId });
    });

    socket.on("log", (data: { type: string; message: string }) => {
      setLogs((prevLogs) => [...prevLogs, data]);
    });

    return () => {
      if (roomId) {
        socket.emit("leave", { room_id: roomId });
      }
      socket.disconnect();
    };
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white">
      <h1 className="text-3xl font-bold mb-6">Upload a Python Script</h1>
      <form
        className="flex flex-col items-center space-y-4 bg-gray-800 p-6 rounded-lg shadow-lg"
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
          disabled={isUploading}
          className={`py-2 px-4 rounded-md ${isUploading ? "bg-gray-500" : "bg-blue-500 hover:bg-blue-600"
            }`}
        >
          {isUploading ? "Uploading..." : "Submit"}
        </button>
      </form>
      <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow-md w-full max-w-3xl">
        <h2 className="text-lg font-bold mb-2">Terminal Output:</h2>
        <div
          ref={terminalRef}
          className="h-64 overflow-y-auto bg-black font-mono p-4 rounded"
          style={{ whiteSpace: "pre-wrap" }}
        >
          {logs.length > 0
            ? logs.map((log, index) => (
              <div
                key={index}
                style={{
                  color: log.type === "stdout" ? "white" : "red",
                }}
              >
                {log.message}
              </div>
            ))
            : "Waiting for logs..."}
        </div>
      </div>
    </div>
  );
};

export default App;