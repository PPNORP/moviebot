import { motion } from "framer-motion";
import { Star } from "lucide-react";

const MovieCard = ({ movie, index }) => {
  const fallbackPoster = "https://images.unsplash.com/photo-1536440136628-849c177e76a1?auto=format&fit=crop&q=80&w=800";

  return (
    <motion.div
      variants={{
        hidden: { y: 20, opacity: 0 },
        visible: { y: 0, opacity: 1 },
      }}
      whileHover={{ scale: 1.05, y: -8 }}
      transition={{ type: "spring", stiffness: 300 }}
      className="bg-white rounded-2xl overflow-hidden shadow-md hover:shadow-xl transition-shadow cursor-pointer"
      data-testid={`movie-card-${index}`}
    >
      {/* Poster */}
      <div className="relative aspect-[2/3] overflow-hidden bg-[#F4F4F5]">
        <img
          src={movie.poster || fallbackPoster}
          alt={movie.title}
          className="w-full h-full object-cover"
        />
        {movie.rating && (
          <div className="absolute top-3 right-3 bg-black/70 backdrop-blur-sm px-2 py-1 rounded-full flex items-center gap-1">
            <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
            <span className="text-xs text-white font-semibold">{movie.rating.toFixed(1)}</span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-4">
        <h3 className="font-bold text-[#18181B] text-sm line-clamp-2 mb-1 leading-tight">
          {movie.title}
        </h3>
        {movie.year && (
          <p className="text-xs text-[#71717A] font-medium">{movie.year}</p>
        )}
      </div>
    </motion.div>
  );
};

export default MovieCard;