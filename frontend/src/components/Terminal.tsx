import { useEffect, useRef } from "react";
import { Terminal } from "xterm";
import { WebLinksAddon } from "xterm-addon-web-links";
import { SearchAddon } from "xterm-addon-search";
import "xterm/css/xterm.css";
import { FitAddon } from "xterm-addon-fit";
import { io, Socket } from "socket.io-client";

import UploadButton from "./UploadButton";

const backendUrl = import.meta.env.VITE_BACKEND_URL;

export default function TerminalComponent() {
  const terminalRef = useRef<HTMLDivElement>(null);
  const socketRef = useRef<Socket>(null);

  const handleLogout = async () => {
    await fetch(`${backendUrl}/logout`, {
      credentials: "include",
    });
    window.location.href = "/";
  };

  useEffect(() => {
    if (!terminalRef.current) return;

    const term = new Terminal({
      cursorBlink: true,
      macOptionIsMeta: true,
      scrollback: 1000,
    });
    const webLinks = new WebLinksAddon();
    const search = new SearchAddon();
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);

    term.loadAddon(webLinks);
    term.loadAddon(search);

    term.open(terminalRef.current);
    requestAnimationFrame(() => {
      fitAddon.fit();
      term.focus();
    });

    term.writeln("Welcome to paas!");

    const socket = io(backendUrl, {
      withCredentials: true,
    });
    socketRef.current = socket;

    term.onData((data) => {
      socket.emit("pty-input", { input: data });
    });

    socket.on("pty-output", (data: { output: string }) => {
      term.write(data.output);
    });

    return () => {
      socket.disconnect();
      term.dispose();
    };
  }, []);

  return (
    <div className="w-[calc(100%-2rem)] md:w-full max-w-screen-md h-full flex flex-col items-center justify-center">
      <div className="w-full flex justify-between items-center mb-4">
        <UploadButton />
        <button
          onClick={handleLogout}
          className="mb-2 px-4 py-1 rounded bg-red-500 text-white"
        >
          Logout
        </button>
      </div>
      <div
        ref={terminalRef}
        className="border border-gray-300 rounded-sm py-1 px-2 bg-black w-full h-2/3 mx-2 sm:mx-4"
      />
    </div>
  );
}
