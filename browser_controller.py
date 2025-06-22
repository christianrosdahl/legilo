import os
import platform
import plistlib
import unicodedata
import urllib.parse
import webbrowser


class BrowserController:
    """
    Open URLs in your default browser.
    Reuses the first opened tab for some browsers on macOS (for default config).
    """

    def __init__(self, open_urls_in_same_tab=True):
        self.open_urls_in_same_tab = open_urls_in_same_tab
        self.has_opened_new_browser_tab = False
        self.default_browser = self.detect_default_browser()

    def detect_default_browser(self):
        if platform.system() != "Darwin":
            return None
        try:
            plist_path = os.path.expanduser(
                "~/Library/Preferences/com.apple.LaunchServices/com.apple.launchservices.secure.plist"
            )
            with open(plist_path, "rb") as f:
                plist = plistlib.load(f)

            handlers = plist.get("LSHandlers", [])
            bundle_id = None

            # Prefer https over http, fallback to http
            for scheme in ("https", "http"):
                for handler in handlers:
                    if handler.get("LSHandlerURLScheme") == scheme:
                        bundle_id = handler.get("LSHandlerRoleAll")
                        if bundle_id:
                            break
                if bundle_id:
                    break

            # Map known bundle IDs to human-readable names
            bundle_map = {
                "com.google.chrome": "Google Chrome",
                "com.brave.browser": "Brave Browser",
                "com.vivaldi.vivaldi": "Vivaldi",
                "org.mozilla.firefox": "Firefox",
                "com.apple.safari": "Safari",
            }

            return bundle_map.get(bundle_id, None)
        except Exception as e:
            print("Error detecting default browser:", e)
            return None

    def open_url(self, url):
        """Open URL in same tab if possible on macOS with supported browsers"""
        url = self.safe_url_for_browser(url)
        if (
            platform.system() == "Darwin"
            and self.open_urls_in_same_tab
            and self.has_opened_new_browser_tab
        ):
            if self.default_browser in {"Google Chrome", "Brave Browser", "Vivaldi"}:
                script = f"""
                tell application "{self.default_browser}"
                    tell front window
                        set URL of active tab to "{url}"
                    end tell
                end tell
                """
            elif self.default_browser == "Safari":
                script = f"""
                tell application "Safari"
                    tell front document
                        set URL to "{url}"
                    end tell
                end tell
                """
            else:
                return webbrowser.open(url)

            osapipe = os.popen("osascript", "w")
            if osapipe is None:
                return False

            osapipe.write(script)
            rc = osapipe.close()
            return not rc
        else:
            webbrowser.open(url)
            self.has_opened_new_browser_tab = True
            return True

    def safe_url_for_browser(self, url):
        # Normalize to NFC to ensure precomposed characters
        normalized = unicodedata.normalize("NFC", url)
        # Percent-encode everything except standard URL characters
        return urllib.parse.quote(normalized, safe=":/?#[]@!$&'()*+,;=%")
