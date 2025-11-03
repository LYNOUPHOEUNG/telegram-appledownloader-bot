import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import logging

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text('Send me a video URL from YouTube, TikTok, or Facebook, and I\'ll download it in HD!')

async def download_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download the video from the URL and send it to the user."""
    url = update.message.text
    if not url.startswith('http'):
        await update.message.reply_text('Please send a valid URL.')
        return

    await update.message.reply_text('Downloading... This might take a moment.')
    
    video_file = None # To store filename for cleanup

    try:
        # yt-dlp options for best HD video + audio
        ydl_opts = {
            'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]', # Limit to 1080p for file size
            'outtmpl': '%(id)s.%(ext)s', # Use video ID for unique filename
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4', # Ensure output is mp4
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Starting download for URL: {url}")
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # After download, filename might be .mkv, but merge_output_format should handle it.
            # Let's find the final file.
            video_file = os.path.splitext(filename)[0] + ".mp4"
            if not os.path.exists(video_file):
                 video_file = filename # Fallback if mp4 wasn't created

            logger.info(f"Download complete. File: {video_file}")


        # Check file size (Telegram limit: 50MB for bots)
        if os.path.getsize(video_file) > 50 * 1024 * 1024:
            await update.message.reply_text('Sorry, the video is larger than 50MB and can\'t be sent via Telegram bot API.')
            logger.warning(f"File {video_file} is too large for Telegram.")
            return

        # Send the video
        logger.info(f"Sending video: {video_file}")
        await update.message.reply_video(video=open(video_file, 'rb'), supports_streaming=True, read_timeout=100, write_timeout=100)
        logger.info("Video sent successfully.")

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"DownloadError: {str(e)}")
        await update.message.reply_text(f'Error downloading video. Make sure the URL is valid and public.')
    except Exception as e:
        logger.error(f"General error: {str(e)}")
        await update.message.reply_text(f'An error occurred: {str(e)}. Please try again.')
    
    finally:
        # Clean up the file after sending or if an error occurred
        if video_file and os.path.exists(video_file):
            os.remove(video_file)
            logger.info(f"Cleaned up file: {video_file}")
            # yt-dlp might leave behind other parts, let's clean those too if they exist
            base_name = os.path.splitext(filename)[0]
            for ext in ['.mkv', '.webm', '.m4a']:
                temp_file = base_name + ext
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.info(f"Cleaned up temp file: {temp_file}")


def main() -> None:
    """Start the bot."""
    # Use the token from the image
    application = Application.builder().token('7813042819:AAHQcQeB3S4hCaZLxdO3sZZqerUXzNRiQjU').build()

    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send))

    # Run the bot
    logger.info("Starting bot polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
