import { useEffect, useState } from "react";
import Terminal from "./components/Terminal";
import Login from "./components/Login";

const backendUrl = import.meta.env.VITE_BACKEND_URL;

function App() {
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    fetch(`${backendUrl}/me`, {
      credentials: "include",
    }).then(async (res) => {
      setAuthed(res.ok);
    });
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

export default App;
