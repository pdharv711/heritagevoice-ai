export default function Footer() {
  return (
    <footer className="bg-[#111827] text-white mt-12">
      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">

          {/* Brand */}
          <div>
            <h2 className="text-xl font-bold">
              <span className="text-pink-500">HV</span>{" "}
              HeritageVoice <span className="text-pink-500">AI</span>
            </h2>

            <p className="text-gray-400 mt-2 text-sm">
              Bringing India's Heritage to Life with AI
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="font-semibold text-lg mb-3">
              Quick Links
            </h3>

            <div className="space-y-2 text-sm text-gray-400">
              <p>Home</p>
              <p>Identify</p>
              <p>Chat</p>
              <p>About</p>
            </div>
          </div>

          {/* Developer */}
          <div>
            <h3 className="font-semibold text-lg mb-3">
              Developed By
            </h3>

            <p className="text-pink-500 text-lg font-bold">
              Patel Dharv
            </p>

            <p className="text-gray-400 text-sm mt-2">
              Passionate Developer & AI Enthusiast
            </p>
          </div>

        </div>

        {/* Copyright */}
        <div className="border-t border-gray-700 mt-8 pt-5 text-center">
          <p className="text-gray-400 text-sm">
            © 2026 HeritageVoice AI. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
