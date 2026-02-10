import { useState } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import ChatInterface from "@/components/ChatInterface";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ChatInterface />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;