import { useEffect, useRef } from "react";
import { Terminal } from "xterm";
import { WebLinksAddon } from "xterm-addon-web-links";
import { SearchAddon } from "xterm-addon-search";
import "xterm/css/xterm.css";
import { io, Socket } from "socket.io-client";

const backendUrl = import.meta.env.VITE_BACKEND_URL;

export default function TerminalComponent() {
  const terminalRef = useRef<HTMLDivElement>(null);
  const socketRef = useRef<Socket>(null);

  useEffect(() => {
    if (!terminalRef.current) return;

    const term = new Terminal({
      cursorBlink: true,
      macOptionIsMeta: true,
      scrollback: 1000,
    });
    const webLinks = new WebLinksAddon();
    const search = new SearchAddon();

    term.loadAddon(webLinks);
    term.loadAddon(search);

    term.open(terminalRef.current);
    requestAnimationFrame(() => {
      term.resize(70, 24);
    });

    term.writeln("Welcome to paas!");

    const socket = io(backendUrl);
    socketRef.current = socket;

    term.onData((data) => {
      socket.emit("pty-input", { input: data });
    });

    socket.on("pty-output", (data: { output: string }) => {
      term.write(data.output);
    });

    // optionally notify backend of fixed size
    // socket.on("connect", () => {
    //   socket.emit("resize", { cols: 40, rows: 20 });
    // });

    return () => {
      socket.disconnect();
      term.dispose();
    };
  }, []);

  return (
    <div
      ref={terminalRef}
      style={{ width: "640px", height: "410px" }} // roughly fits 40x20
      className="border border-gray-300"
    />
  );
}
