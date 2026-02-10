import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Film, RefreshCw, Loader2 } from "lucide-react";
import axios from "axios";
import MovieCard from "./MovieCard";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const MessageBubble = ({ content, variant, index }) => {
  const isUser = variant === "user";
  
  return (
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ delay: index * 0.05 }}
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}
    >
      <div
        className={`max-w-[75%] px-5 py-3 rounded-2xl shadow-sm ${
          isUser
            ? "bg-[#F97316] text-white rounded-tr-sm"
            : "bg-white border border-[#E4E4E7] text-[#18181B] rounded-tl-sm"
        }`}
        style={{ whiteSpace: "pre-wrap" }}
      >
        {content}
      </div>
    </motion.div>
  );
};

const ChatInterface = () => {
  const [messages, setMessages] = useState([
    { content: "สวัสดี! พิมพ์ start เพื่อเริ่มหาหนังที่ใช่สำหรับคุณ 🎬", variant: "bot" },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [movies, setMovies] = useState([]);
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, movies]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = input.trim();
    setMessages((prev) => [...prev, { content: userMessage, variant: "user" }]);
    setInput("");

    try {
      const response = await axios.post(`${API}/chat`, { message: userMessage });
      setMessages((prev) => [...prev, { content: response.data.reply, variant: "bot" }]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { content: "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง", variant: "bot" },
      ]);
    }
  };

  const handleRecommend = async () => {
    setIsLoading(true);
    setMessages((prev) => [...prev, { content: "กำลังหาหนังให้... 🍿", variant: "bot" }]);

    try {
      const response = await axios.get(`${API}/recommend`);
      const { movies: movieList } = response.data;
      setMovies(movieList);
      setMessages((prev) => [
        ...prev,
        {
          content: `เจอแล้ว! นี่คือ ${movieList.length} เรื่องที่น่าสนใจสำหรับคุณ 🎥`,
          variant: "bot",
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          content: error.response?.data?.detail || "เกิดข้อผิดพลาด กรุณาตอบคำถามก่อน (พิมพ์ start)",
          variant: "bot",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = async () => {
    setMessages([{ content: "กำลังรีเซ็ต...", variant: "bot" }]);
    setMovies([]);
    try {
      const response = await axios.post(`${API}/chat`, { message: "reset" });
      setMessages([{ content: response.data.reply, variant: "bot" }]);
    } catch (error) {
      setMessages([{ content: "เกิดข้อผิดพลาด", variant: "bot" }]);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] py-6 px-4 md:px-8">
      {/* Header */}
      <div className="max-w-6xl mx-auto mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-gradient-to-br from-[#F97316] to-[#F43F5E] rounded-2xl flex items-center justify-center">
              <Film className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-[#18181B] tracking-tight">MovieBot</h1>
              <p className="text-sm text-[#71717A]">แนะนำหนังที่ใช่สำหรับคุณ</p>
            </div>
          </div>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-[#E4E4E7] text-[#18181B] font-medium hover:bg-[#F4F4F5] transition-colors"
            data-testid="reset-button"
          >
            <RefreshCw className="w-4 h-4" />
            Reset
          </motion.button>
        </div>
      </div>

      {/* Chat Container */}
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-3xl shadow-lg border border-[#E4E4E7] overflow-hidden">
          {/* Messages Area */}
          <div className="h-[60vh] overflow-y-auto p-6">
            <AnimatePresence>
              {messages.map((msg, index) => (
                <MessageBubble
                  key={index}
                  content={msg.content}
                  variant={msg.variant}
                  index={index}
                />
              ))}
            </AnimatePresence>
            <div ref={chatEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-[#E4E4E7] p-4 bg-white/80 backdrop-blur-xl">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder="พิมพ์คำตอบ..."
                className="flex-1 px-4 py-3 rounded-full border border-[#E4E4E7] bg-white text-[#18181B] placeholder:text-[#71717A] focus:outline-none focus:ring-2 focus:ring-[#F97316] focus:border-transparent transition-all"
                data-testid="message-input"
              />
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleSend}
                className="px-6 py-3 rounded-full bg-[#3B82F6] text-white font-semibold hover:bg-[#2563EB] transition-colors flex items-center gap-2"
                data-testid="send-button"
              >
                <Send className="w-4 h-4" />
                Send
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleRecommend}
                disabled={isLoading}
                className="px-6 py-3 rounded-full bg-[#F97316] text-white font-semibold hover:bg-[#EA580C] transition-colors flex items-center gap-2 disabled:opacity-50"
                data-testid="recommend-button"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Loading
                  </>
                ) : (
                  <>
                    <Film className="w-4 h-4" />
                    Recommend
                  </>
                )}
              </motion.button>
            </div>
          </div>
        </div>
      </div>

      {/* Movies Grid */}
      {movies.length > 0 && (
        <div className="max-w-6xl mx-auto mt-12">
          <h2 className="text-2xl font-bold text-[#18181B] mb-6">หนังที่แนะนำ</h2>
          <motion.div
            initial="hidden"
            animate="visible"
            variants={{
              visible: {
                transition: {
                  staggerChildren: 0.08,
                },
              },
            }}
            className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6"
          >
            {movies.map((movie, index) => (
              <MovieCard key={index} movie={movie} index={index} />
            ))}
          </motion.div>
        </div>
      )}
    </div>
  );
};

export default ChatInterface;