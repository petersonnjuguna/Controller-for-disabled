import speech_recognition as sr
import webbrowser
import time
import pyautogui
import keyboard
import google.generativeai as genai
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import re
import threading
import logging
import urllib.parse
import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk
import io
import base64
from googletrans import Translator  # For translating Tamil commands to English

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DisplayWindow:
    def __init__(self, root):
        """Initialize the display window."""
        self.root = root
        self.root.title("Voice Commands and Page Analysis")
        self.root.geometry("800x600")
        
        # Split the window into two frames
        self.top_frame = tk.Frame(root)
        self.top_frame.pack(fill=tk.BOTH, expand=True)
        
        # Command display area
        self.command_frame = tk.LabelFrame(self.top_frame, text="Recognized Commands")
        self.command_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.command_text = scrolledtext.ScrolledText(self.command_frame, wrap=tk.WORD)
        self.command_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tamil explanation area
        self.tamil_frame = tk.LabelFrame(self.top_frame, text="Tamil Explanation")
        self.tamil_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tamil_text = scrolledtext.ScrolledText(self.tamil_frame, wrap=tk.WORD)
        self.tamil_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Screenshot area
        self.screenshot_frame = tk.LabelFrame(root, text="Current Page")
        self.screenshot_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.screenshot_label = tk.Label(self.screenshot_frame)
        self.screenshot_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Set up tags for different types of text
        self.command_text.tag_configure("command", foreground="blue", font=("Arial", 12, "bold"))
        self.command_text.tag_configure("info", foreground="green", font=("Arial", 12))
        self.command_text.tag_configure("error", foreground="red", font=("Arial", 12))
        
        # Configure Tamil text font
        self.tamil_text.configure(font=("Arial Unicode MS", 12))
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.running = True
    
    def add_command(self, text):
        """Add a recognized command to the display."""
        self.command_text.insert(tk.END, f"Command: {text}\n", "command")
        self.command_text.see(tk.END)
    
    def add_info(self, text):
        """Add info text to the display."""
        self.command_text.insert(tk.END, f"Info: {text}\n", "info")
        self.command_text.see(tk.END)
    
    def add_error(self, text):
        """Add error text to the display."""
        self.command_text.insert(tk.END, f"Error: {text}\n", "error")
        self.command_text.see(tk.END)
    
    def update_tamil(self, text):
        """Update the Tamil explanation."""
        self.tamil_text.delete(1.0, tk.END)
        self.tamil_text.insert(tk.END, text)
    
    def update_screenshot(self, image_data):
        """Update the screenshot display."""
        try:
            img = Image.open(io.BytesIO(image_data))
            # Resize the image to fit in the label
            width, height = 780, 300
            img = img.resize((width, height), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.screenshot_label.configure(image=photo)
            self.screenshot_label.image = photo  # Keep a reference to avoid garbage collection
        except Exception as e:
            logger.error(f"Error updating screenshot: {e}")
    
    def on_close(self):
        """Handle window close event."""
        self.running = False
        self.root.destroy()

class VoiceWebController:
    def __init__(self, api_key):
        """Initialize the voice web controller with Gemini API."""
        self.recognizer = sr.Recognizer()
        self.microphone = self.select_microphone()  # Select the correct microphone
        self.driver = None
        self.listening = False
        self.thread = None
        self.numbered_mode = False
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('models/gemini-2.0-flash')
        
        # Initialize display window
        self.root = tk.Tk()
        self.display = DisplayWindow(self.root)
        
        # Initialize browser
        self.setup_browser()
        
        # Start the screenshot updater
        self.page_update_thread = threading.Thread(target=self.update_page_periodically)
        self.page_update_thread.daemon = True
        self.page_update_thread.start()
        
        # Available commands
        self.commands = {
            "click numbers": self.show_numbered_elements,
            "numbers": self.show_numbered_elements,  # Alternative command
            "click number": self.click_by_number,
            "number": self.click_by_number,  # Alternative command
            "scroll down": self.scroll_down,
            "scroll up": self.scroll_up,
            "click": self.click_element,
            "click button": self.click_button,  # New command for clicking buttons
            "type": self.type_text,
            "search": self.search,
            "go to": self.navigate,
            "open": self.open_website,
            "new tab": self.open_new_tab,
            "switch tab": self.switch_tab,
            "close tab": self.close_tab,
            "back": self.go_back,
            "forward": self.go_forward,
            "refresh": self.refresh_page,
            "play": self.play_media,
            "pause": self.pause_media,
            "stop": self.stop_listening,
            "analyze page": self.analyze_page,
            "show hints": self.show_hints,
            "help": self.show_help
        }

        # Tamil to English command mapping
        self.tamil_commands = {
            "யூடியூப் திற": "open youtube",  # "YouTube-aiy thera" -> "open youtube"
            "கூகிள் திற": "open google",  # "Google-aiy thera" -> "open google"
            "ஸ்க்ரோல் கீழ்": "scroll down",  # "Scroll keel" -> "scroll down"
            "ஸ்க்ரோல் மேல்": "scroll up",  # "Scroll mel" -> "scroll up"
            "பின்னால் செல்": "back",  # "Pinnal sel" -> "back"
            "முன்னால் செல்": "forward",  # "Munnāl sel" -> "forward"
            "புதிய தாவல் திற": "new tab",  # "Puthiya thaval thera" -> "new tab"
            "தாவல் மாறு": "switch tab",  # "Thaval maaru" -> "switch tab"
            "தாவல் மூடு": "close tab",  # "Thaval moodu" -> "close tab"
            "பக்கம் புதுப்பி": "refresh",  # "Page puduppi" -> "refresh"
            "தேடு": "search",  # "Thedu" -> "search"
            "உதவி": "help",  # "Udhavi" -> "help"
        }

        # Initialize translator
        self.translator = Translator()
    
    def select_microphone(self):
        """Allow the user to select the correct microphone."""
        mic_list = sr.Microphone.list_microphone_names()
        if not mic_list:
            logger.error("No microphones found!")
            raise Exception("No microphones available.")
        
        logger.info("Available microphones:")
        for i, mic in enumerate(mic_list):
            logger.info(f"{i}: {mic}")
        
        mic_index = 0  # Default to the first microphone
        try:
            mic_index = int(input("Enter the index of the microphone you want to use: "))
            if mic_index < 0 or mic_index >= len(mic_list):
                logger.warning("Invalid index. Using default microphone (index 0).")
                mic_index = 0
        except ValueError:
            logger.warning("Invalid input. Using default microphone (index 0).")
        
        logger.info(f"Using microphone: {mic_list[mic_index]}")
        return sr.Microphone(device_index=mic_index)
    
    def update_page_periodically(self):
        """Update the page screenshot and Tamil explanation periodically."""
        if not hasattr(self, 'display') or not self.display.running:
            return
        
        try:
            self.update_page_info()
        except Exception as e:
            logger.error(f"Error in update thread: {e}")
        
        # Schedule the next update
        self.root.after(3000, self.update_page_periodically)  # Update every 3 seconds
    
    def update_page_info(self):
        """Update the page screenshot and Tamil explanation."""
        if not self.driver:
            return
            
        try:
            # Take a screenshot
            screenshot = self.driver.get_screenshot_as_png()
            self.display.update_screenshot(screenshot)
            
            # Get page title and visible text
            title = self.driver.title
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            truncated_text = body_text[:2000] if len(body_text) > 2000 else body_text
            
            # Get the URL
            url = self.driver.current_url
            
            # Count elements
            links = len(self.driver.find_elements(By.TAG_NAME, "a"))
            buttons = len(self.driver.find_elements(By.TAG_NAME, "button"))
            images = len(self.driver.find_elements(By.TAG_NAME, "img"))
            
            # Generate Tamil explanation using Gemini
            prompt = f"""
            You are a Tamil language assistant. Describe this webpage in Tamil language.
            
            URL: {url}
            Title: {title}
            Number of links: {links}
            Number of buttons: {buttons}
            Number of images: {images}
            
            Page content preview: {truncated_text}
            
            Provide a short summary (2-3 paragraphs) in Tamil language explaining:
            1. What this webpage is about
            2. What main elements are visible
            3. What actions the user can take on this page
            
            Focus on being helpful to a Tamil-speaking user.
            """
            
            try:
                response = self.model.generate_content(prompt)
                tamil_explanation = response.text
                self.display.update_tamil(tamil_explanation)
            except Exception as e:
                logger.error(f"Error generating Tamil explanation: {e}")
                self.display.update_tamil("Error generating Tamil explanation: " + str(e))
                
        except Exception as e:
            logger.error(f"Error updating page info: {e}")
    
    def setup_browser(self):
        """Setup the browser with Selenium WebDriver."""
        try:
            edge_options = EdgeOptions()
            edge_options.add_argument("--start-maximized")  # Maximize the browser window
            edge_options.add_argument("--disable-infobars")  # Disable infobars
            edge_options.add_argument("--disable-extensions")  # Disable extensions
            
            self.driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=edge_options)
            logger.info("Browser initialized successfully")
            self.display.add_info("Browser initialized successfully")
        except Exception as e:
            error_msg = f"Error initializing browser: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.driver = None  # Ensure driver is explicitly set to None if initialization fails
            raise
    
    def show_numbered_elements(self, param=""):
        """Show numbers on all clickable elements."""
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
            
            logger.info("Showing numbered elements")
            self.display.add_info("Showing numbered elements")
            
            # Find all clickable elements
            elements = self.driver.find_elements(By.XPATH, "//a | //button | //input[@type='button'] | //input[@type='submit'] | //div[@role='button'] | //span[@role='button']")
            
            # Create a JavaScript function to add numbered overlays
            js_code = """
            // Remove any existing overlays
            var existingOverlays = document.querySelectorAll('.clickable-overlay');
            existingOverlays.forEach(function(overlay) {
                overlay.remove();
            });
            
            // Create style for overlays
            var style = document.createElement('style');
            style.innerHTML = `
                .clickable-overlay {
                    position: absolute;
                    background-color: rgba(255, 0, 0, 0.7);
                    color: white;
                    border-radius: 50%;
                    width: 25px;
                    height: 25px;
                    text-align: center;
                    line-height: 25px;
                    font-weight: bold;
                    z-index: 10000;
                    pointer-events: none;
                    font-size: 14px;
                }
            `;
            document.head.appendChild(style);
            
            // Function to create overlays
            function createOverlay(element, number) {
                var rect = element.getBoundingClientRect();
                // Only create overlay if the element is visible
                if (rect.width > 0 && rect.height > 0 && element.offsetParent !== null) {
                    var overlay = document.createElement('div');
                    overlay.className = 'clickable-overlay';
                    overlay.textContent = number;
                    overlay.style.left = (rect.left + window.scrollX) + 'px';
                    overlay.style.top = (rect.top + window.scrollY) + 'px';
                    document.body.appendChild(overlay);
                    return true;
                }
                return false;
            }
            
            // Clear existing elements array
            window.clickableElements = [];
            
            // Create overlays for each element
            var count = 0;
            for (var i = 0; i < arguments[0].length; i++) {
                if (count < 30) {  // Limit to first 30 elements
                    if (createOverlay(arguments[0][i], count + 1)) {
                        window.clickableElements.push(arguments[0][i]);
                        count++;
                    }
                }
            }
            
            // Return the number of overlays created
            return count;
            """
            
            # Execute the JavaScript and get the number of elements labeled
            num_elements = self.driver.execute_script(js_code, elements)
            info_msg = f"Added number overlays to {num_elements} clickable elements"
            logger.info(info_msg)
            self.display.add_info(info_msg)
            
            # Set numbered mode to True
            self.numbered_mode = True
            
            # Automatic timeout to clear numbers after 15 seconds
            threading.Timer(15, self.clear_numbered_elements).start()
            
        except Exception as e:
            error_msg = f"Error showing numbered elements: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def clear_numbered_elements(self):
        """Clear the numbered overlays."""
        try:
            if self.numbered_mode and self.driver:
                js_code = """
                var existingOverlays = document.querySelectorAll('.clickable-overlay');
                existingOverlays.forEach(function(overlay) {
                    overlay.remove();
                });
                """
                self.driver.execute_script(js_code)
                logger.info("Cleared numbered overlays")
                self.display.add_info("Cleared numbered overlays")
                self.numbered_mode = False
        except Exception as e:
            error_msg = f"Error clearing numbered elements: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
    
    def click_by_number(self, param=""):
        """Click an element by its assigned number."""
        if not self.numbered_mode:
            info_msg = "Numbered mode is not active. Say 'numbers' or 'click numbers' first"
            logger.info(info_msg)
            self.display.add_info(info_msg)
            return
        
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            # Extract the number from the command
            if param.isdigit():
                number = int(param)
            else:
                # Try to extract the number from the text
                match = re.search(r'\d+', param)
                if match:
                    number = int(match.group())
                else:
                    info_msg = "No valid number found in the command"
                    logger.info(info_msg)
                    self.display.add_info(info_msg)
                    return
            
            # Execute JavaScript to click the element with the given number
            js_code = """
            var elements = window.clickableElements;
            var index = arguments[0] - 1;
            
            if (elements && index >= 0 && index < elements.length) {
                elements[index].click();
                return true;
            }
            return false;
            """
            result = self.driver.execute_script(js_code, number)
            
            if result:
                info_msg = f"Clicked element number {number}"
                logger.info(info_msg)
                self.display.add_info(info_msg)
                # Clear the numbered overlays after clicking
                self.clear_numbered_elements()
            else:
                info_msg = f"No element found with number {number}"
                logger.info(info_msg)
                self.display.add_info(info_msg)
        except Exception as e:
            error_msg = f"Error clicking by number: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def click_button(self, button_name):
        """Click a button by its visible text or accessible name."""
        if not button_name:
            info_msg = "No button name specified"
            logger.info(info_msg)
            self.display.add_info(info_msg)
            return
        
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
            
            # JavaScript to generate XPath
            generate_xpath_script = """
            function getXPath(element) {
                if (element.id !== '') {
                    return '//*[@id="' + element.id + '"]';
                }
                if (element === document.body) {
                    return '/html/body';
                }

                let ix = 0;
                let siblings = element.parentNode.childNodes;
                for (let i = 0; i < siblings.length; i++) {
                    let sibling = siblings[i];
                    if (sibling === element) {
                        return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                                                ix++;
                    }
                }
            }
            return getXPath(arguments[0]);
            """
            
            # Find the button by its visible text or accessible name
            button = self.driver.find_element(By.XPATH, f"//button[contains(text(), '{button_name}') or contains(@aria-label, '{button_name}')]")
            
            # Generate the XPath of the button
            xpath = self.driver.execute_script(generate_xpath_script, button)
            logger.info(f"Generated XPath for button: {xpath}")
            self.display.add_info(f"Generated XPath for button: {xpath}")
            
            # Click the button using the generated XPath
            self.driver.find_element(By.XPATH, xpath).click()
            info_msg = f"Clicked button: {button_name}"
            logger.info(info_msg)
            self.display.add_info(info_msg)
        except Exception as e:
            error_msg = f"Error clicking button: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def scroll_down(self, param=""):
        """Scroll down the page."""
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            self.driver.execute_script("window.scrollBy(0, 500);")
            logger.info("Scrolled down")
            self.display.add_info("Scrolled down")
        except Exception as e:
            error_msg = f"Error scrolling down: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def scroll_up(self, param=""):
        """Scroll up the page."""
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            self.driver.execute_script("window.scrollBy(0, -500);")
            logger.info("Scrolled up")
            self.display.add_info("Scrolled up")
        except Exception as e:
            error_msg = f"Error scrolling up: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def click_element(self, param=""):
        """Click an element on the page."""
        if not param:
            info_msg = "No element specified to click"
            logger.info(info_msg)
            self.display.add_info(info_msg)
            return
        
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            # Find the element by text (you can modify this to use other selectors)
            element = self.driver.find_element(By.XPATH, f"//*[contains(text(), '{param}')]")
            element.click()
            info_msg = f"Clicked element: {param}"
            logger.info(info_msg)
            self.display.add_info(info_msg)
        except Exception as e:
            error_msg = f"Error clicking element: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def type_text(self, param=""):
        """Type text into the focused element."""
        if not param:
            info_msg = "No text specified to type"
            logger.info(info_msg)
            self.display.add_info(info_msg)
            return
        
        try:
            pyautogui.write(param)
            info_msg = f"Typed text: {param}"
            logger.info(info_msg)
            self.display.add_info(info_msg)
        except Exception as e:
            error_msg = f"Error typing text: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
    
    def search(self, param=""):
        """Perform a web search."""
        if not param:
            info_msg = "No search query specified"
            logger.info(info_msg)
            self.display.add_info(info_msg)
            return
        
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(param)}"
            self.driver.get(search_url)
            info_msg = f"Performed search for: {param}"
            logger.info(info_msg)
            self.display.add_info(info_msg)
        except Exception as e:
            error_msg = f"Error performing search: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def navigate(self, url):
        """Navigate to a URL."""
        if not url:
            info_msg = "No URL specified"
            logger.info(info_msg)
            self.display.add_info(info_msg)
            return
        
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Parse and rebuild the URL to ensure it's valid
            parsed_url = urllib.parse.urlparse(url)
            rebuilt_url = urllib.parse.urlunparse(parsed_url)

            self.driver.get(rebuilt_url)
            info_msg = f"Navigated to {rebuilt_url}"
            logger.info(info_msg)
            self.display.add_info(info_msg)
        except Exception as e:
            error_msg = f"Error navigating to URL: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def open_website(self, param=""):
        """Open any website."""
        if not param:
            info_msg = "No website specified"
            logger.info(info_msg)
            self.display.add_info(info_msg)
            return
        
        website = param.lower().strip()
        
        # Common TLDs to check
        common_tlds = [".com", ".org", ".net", ".edu", ".gov", ".co", ".io"]
        
        # Check if the site already has a TLD
        has_tld = any(website.endswith(tld) for tld in common_tlds)
        
        # If no TLD, assume .com
        if not has_tld and "." not in website:
            website = website + ".com"
        
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            # Add protocol if missing
            if not website.startswith(('http://', 'https://')):
                website = 'https://' + website
            
            self.driver.get(website)
            info_msg = f"Opened website: {website}"
            logger.info(info_msg)
            self.display.add_info(info_msg)
        except Exception as e:
            error_msg = f"Error opening website {website}: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def open_new_tab(self, param=""):
        """Open a new browser tab."""
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            # Open a new tab
            self.driver.execute_script("window.open('about:blank', '_blank');")
            # Switch to the new tab
            self.driver.switch_to.window(self.driver.window_handles[-1])
            info_msg = "Opened new tab"
            logger.info(info_msg)
            self.display.add_info(info_msg)
            
            # If a URL is specified, navigate to it
            if param:
                self.open_website(param)
        except Exception as e:
            error_msg = f"Error opening new tab: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def switch_tab(self, param=""):
        """Switch between tabs."""
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            if not param or param == "next":
                # Get the current window handle
                current = self.driver.current_window_handle
                handles = self.driver.window_handles
                
                # Find the next handle
                current_index = handles.index(current)
                next_index = (current_index + 1) % len(handles)
                
                # Switch to the next tab
                self.driver.switch_to.window(handles[next_index])
                info_msg = "Switched to next tab"
                logger.info(info_msg)
                self.display.add_info(info_msg)
            elif param == "previous" or param == "prev":
                # Get the current window handle
                current = self.driver.current_window_handle
                handles = self.driver.window_handles
                
                # Find the previous handle
                current_index = handles.index(current)
                prev_index = (current_index - 1) % len(handles)
                
                # Switch to the previous tab
                self.driver.switch_to.window(handles[prev_index])
                info_msg = "Switched to previous tab"
                logger.info(info_msg)
                self.display.add_info(info_msg)
            elif param.isdigit():
                # Switch to a specific tab by index
                index = int(param) - 1  # Convert to 0-based index
                handles = self.driver.window_handles
                
                if 0 <= index < len(handles):
                    self.driver.switch_to.window(handles[index])
                    info_msg = f"Switched to tab {index + 1}"
                    logger.info(info_msg)
                    self.display.add_info(info_msg)
                else:
                    info_msg = f"Tab {index + 1} does not exist"
                    logger.info(info_msg)
                    self.display.add_info(info_msg)
        except Exception as e:
            error_msg = f"Error switching tabs: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def close_tab(self, param=""):
        """Close the current tab."""
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            # Get all window handles
            handles = self.driver.window_handles
            
            # Close the current tab
            self.driver.close()
            info_msg = "Closed current tab"
            logger.info(info_msg)
            self.display.add_info(info_msg)
            
            # If there are still tabs open, switch to the first one
            if len(handles) > 1:
                self.driver.switch_to.window(handles[0])
        except Exception as e:
            error_msg = f"Error closing tab: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def go_back(self, param=""):
        """Go back in the browser history."""
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            self.driver.back()
            info_msg = "Navigated back"
            logger.info(info_msg)
            self.display.add_info(info_msg)
        except Exception as e:
            error_msg = f"Error going back: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def go_forward(self, param=""):
        """Go forward in the browser history."""
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            self.driver.forward()
            info_msg = "Navigated forward"
            logger.info(info_msg)
            self.display.add_info(info_msg)
        except Exception as e:
            error_msg = f"Error going forward: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def refresh_page(self, param=""):
        """Refresh the current page."""
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            self.driver.refresh()
            info_msg = "Page refreshed"
            logger.info(info_msg)
            self.display.add_info(info_msg)
        except Exception as e:
            error_msg = f"Error refreshing page: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def play_media(self, param=""):
        """Play media on the page."""
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            # Execute JavaScript to play media
            self.driver.execute_script("document.querySelector('video, audio').play();")
            info_msg = "Media playback started"
            logger.info(info_msg)
            self.display.add_info(info_msg)
        except Exception as e:
            error_msg = f"Error playing media: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def pause_media(self, param=""):
        """Pause media on the page."""
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            # Execute JavaScript to pause media
            self.driver.execute_script("document.querySelector('video, audio').pause();")
            info_msg = "Media playback paused"
            logger.info(info_msg)
            self.display.add_info(info_msg)
        except Exception as e:
            error_msg = f"Error pausing media: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def stop_listening(self, param=""):
        """Stop listening for voice commands."""
        self.listening = False
        info_msg = "Stopped listening for commands"
        logger.info(info_msg)
        self.display.add_info(info_msg)
    
    def analyze_page(self, param=""):
        """Analyze the current page and provide insights."""
        try:
            if not self.driver:
                error_msg = "Browser not initialized"
                logger.error(error_msg)
                self.display.add_error(error_msg)
                self.restart_browser()
                return
                
            # Get page title and URL
            title = self.driver.title
            url = self.driver.current_url
            
            # Get page content
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            truncated_text = body_text[:2000] if len(body_text) > 2000 else body_text
            
            # Count elements
            links = len(self.driver.find_elements(By.TAG_NAME, "a"))
            buttons = len(self.driver.find_elements(By.TAG_NAME, "button"))
            images = len(self.driver.find_elements(By.TAG_NAME, "img"))
            
            # Generate analysis using Gemini
            prompt = f"""
            Analyze this webpage and provide a summary:
            
            URL: {url}
            Title: {title}
            Number of links: {links}
            Number of buttons: {buttons}
            Number of images: {images}
            
            Page content preview: {truncated_text}
            
            Provide a summary of the page content and suggest possible actions the user can take.
            """
            
            response = self.model.generate_content(prompt)
            analysis = response.text
            self.display.add_info(f"Page Analysis:\n{analysis}")
        except Exception as e:
            error_msg = f"Error analyzing page: {e}"
            logger.error(error_msg)
            self.display.add_error(error_msg)
            self.restart_browser()
    
    def show_hints(self, param=""):
        """Show hints for available commands."""
        hints = """
        Available Commands:
        - 'click numbers': Show numbers on clickable elements
        - 'click number [number]': Click an element by its number
        - 'scroll down': Scroll down the page
        - 'scroll up': Scroll up the page
        - 'click [text]': Click an element with the specified text
        - 'click button [button name]': Click a button by its name
        - 'type [text]': Type text into the focused element
        - 'search [query]': Perform a web search
        - 'go to [URL]': Navigate to a URL
        - 'open [website]':
            - 'new tab': Open a new tab
            - 'switch tab': Switch to the next tab
            - 'close tab': Close the current tab
            - 'back': Go back in the browser history
            - 'forward': Go forward in the browser history
            - 'refresh': Refresh the current page
            - 'play': Play media on the page
            - 'pause': Pause media on the page
            - 'stop': Stop listening for commands
            - 'analyze page': Analyze the current page
            - 'show hints': Show this list of commands
            - 'help': Show detailed help
        """
        self.display.add_info(hints)
    
    def show_help(self, param=""):
        """Show detailed help."""
        help_text = """
        Voice Web Controller Help:
        
        This application allows you to control a web browser using voice commands. 
        You can navigate websites, click elements, scroll, and perform various other actions.
        
        Commands:
        - 'click numbers': Show numbers on clickable elements. You can then click an element by saying 'click number [number]'.
        - 'scroll down' / 'scroll up': Scroll the page up or down.
        - 'click [text]': Click an element that contains the specified text.
        - 'click button [button name]': Click a button by its visible text or accessible name.
        - 'type [text]': Type text into the focused input field.
        - 'search [query]': Perform a Google search for the specified query.
        - 'go to [URL]': Navigate to the specified URL.
        - 'open [website]': Open a website (e.g., 'open google.com').
        - 'new tab': Open a new browser tab.
        - 'switch tab': Switch to the next tab.
        - 'close tab': Close the current tab.
        - 'back' / 'forward': Navigate back or forward in the browser history.
        - 'refresh': Refresh the current page.
        - 'play' / 'pause': Play or pause media on the page.
        - 'stop': Stop listening for commands.
        - 'analyze page': Analyze the current page and provide insights.
        - 'show hints': Show a list of available commands.
        - 'help': Show this detailed help message.
        """
        self.display.add_info(help_text)
    
    def restart_browser(self):
        """Restart the browser if it crashes or becomes unresponsive."""
        try:
            if self.driver:
                self.driver.quit()
            self.setup_browser()
        except Exception as e:
            logger.error(f"Error restarting browser: {e}")
    
    def listen_for_commands(self):
        """Listen for voice commands and execute them."""
        self.listening = True
        while self.listening:
            try:
                with self.microphone as source:
                    logger.info("Listening for a command...")
                    self.recognizer.adjust_for_ambient_noise(source)
                    audio = self.recognizer.listen(source)
                
                try:
                    # Recognize Tamil speech
                    command = self.recognizer.recognize_google(audio, language="ta-IN").lower()
                    logger.info(f"Recognized Tamil command: {command}")
                    self.display.add_command(f"Recognized Tamil command: {command}")

                    # Translate Tamil command to English (if needed)
                    english_command = self.translate_tamil_to_english(command)
                    logger.info(f"Translated to English: {english_command}")
                    self.display.add_info(f"Translated to English: {english_command}")

                    # Process the translated command
                    self.process_command(english_command)
                except sr.UnknownValueError:
                    logger.info("Could not understand the audio")
                    self.display.add_error("Could not understand the audio")
                except sr.RequestError as e:
                    logger.error(f"Could not request results from Google Speech Recognition service; {e}")
                    self.display.add_error(f"Speech recognition error: {e}")
            except Exception as e:
                logger.error(f"Error in command listening loop: {e}")
                self.display.add_error(f"Error: {e}")
                time.sleep(1)
    
    def translate_tamil_to_english(self, tamil_command):
        """Translate Tamil commands to English using a predefined mapping or Google Translate."""
        # Check if the command is in the predefined mapping
        if tamil_command in self.tamil_commands:
            return self.tamil_commands[tamil_command]

        # Use Google Translate for dynamic translation (fallback)
        try:
            translation = self.translator.translate(tamil_command, src="ta", dest="en")
            return translation.text.lower()
        except Exception as e:
            logger.error(f"Error translating Tamil command: {e}")
            return tamil_command  # Return the original command if translation fails

    def process_command(self, command):
        """Process the recognized command."""
        # Split the command into action and parameter
        parts = command.split(maxsplit=1)
        action = parts[0]
        param = parts[1] if len(parts) > 1 else ""
        
        # Check if the action is in the commands dictionary
        if action in self.commands:
            self.commands[action](param)
        else:
            self.display.add_info(f"Unknown command: {action}")
    
    def run(self):
        """Run the application."""
        try:
            # Start listening for commands in a separate thread
            self.thread = threading.Thread(target=self.listen_for_commands)
            self.thread.daemon = True
            self.thread.start()
            
            # Start the periodic updates
            self.root.after(0, self.update_page_periodically)
            
            # Start the GUI main loop
            self.root.mainloop()
        except Exception as e:
            logger.error(f"Error running application: {e}")
            self.display.add_error(f"Application error: {e}")
        finally:
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    # Replace with your actual Gemini API key
    API_KEY = "AIzaSyBY5G89TIt9EgTyhv7vQP0TGQT21_fEZdg"
    
    # Initialize and run the voice web controller
    controller = VoiceWebController(API_KEY)
    controller.run()
