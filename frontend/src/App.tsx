import { useEffect, useState } from "react";
import Terminal from "./components/Terminal";
import Login from "./components/Login";

const backendUrl = import.meta.env.VITE_BACKEND_URL;

export default function App() {
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const res = await fetch(`${backendUrl}/me`, { credentials: "include" });
        setAuthed(res.ok);
      } catch {
        setAuthed(false);
      }
    };
    checkAuth();
  }, []);

  if (authed === null)
    return (
      <div className="h-screen w-screen flex items-center justify-center">
        Loading...
      </div>
    );

  if (!authed)
    return (
      <div className="h-screen w-screen flex items-center justify-center flex-col gap-4">
        <div className="text-3xl font-bold tracking-wide">
          Birdflop Server Access
        </div>
        <Login />
      </div>
    );

  return (
    <div className="h-screen w-screen flex flex-col items-center justify-center">
      <Terminal />
    </div>
  );
}
