import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import os
import base64
from io import BytesIO
from PIL import Image, ImageTk
import cv2

class ApiTester(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("API Tester")
        self.geometry("1000x600")

        # Style
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TButton", background="#3498db", foreground="white")
        style.map("TButton", background=[("active", "#2980b9")])

        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="y", padx=5)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=5)

        # API Key
        ttk.Label(left_frame, text="API Key:").pack(pady=2)
        self.api_key_entry = ttk.Entry(left_frame, width=40)
        self.api_key_entry.pack(pady=2)
        self.api_key_entry.insert(0, "YOUR_API_KEY_HERE")

        # Person ID
        ttk.Label(left_frame, text="Person ID:").pack(pady=2)
        self.person_id_entry = ttk.Entry(left_frame, width=40)
        self.person_id_entry.pack(pady=2)

        # Registration
        reg_frame = ttk.LabelFrame(left_frame, text="Register")
        reg_frame.pack(pady=5, padx=5, fill="x")

        self.reg_images_label = ttk.Label(reg_frame, text="No images selected.")
        self.reg_images_label.pack(pady=2)
        ttk.Button(reg_frame, text="Select Images for Registration", command=self.select_reg_images).pack(pady=2)
        ttk.Button(reg_frame, text="Register", command=self.register).pack(pady=2)

        # Verification
        verify_frame = ttk.LabelFrame(left_frame, text="Verify")
        verify_frame.pack(pady=5, padx=5, fill="x")

        self.verify_image_label = ttk.Label(verify_frame, text="No image selected.")
        self.verify_image_label.pack(pady=2)
        ttk.Button(verify_frame, text="Select Image for Verification", command=self.select_verify_image).pack(pady=2)
        ttk.Button(verify_frame, text="Capture from Camera", command=self.capture_for_verification).pack(pady=2)
        ttk.Button(verify_frame, text="Verify", command=self.verify).pack(pady=2)

        # System
        system_frame = ttk.LabelFrame(left_frame, text="System")
        system_frame.pack(pady=5, padx=5, fill="x")
        ttk.Button(system_frame, text="Health Check", command=self.health_check).pack(pady=2)
        ttk.Button(system_frame, text="Delete Person", command=self.delete_person).pack(pady=2)

        # Response
        response_frame = ttk.LabelFrame(right_frame, text="Response")
        response_frame.pack(pady=5, padx=5, fill="x")
        self.response_text = tk.Text(response_frame, wrap="word", height=5, bg="#f0f0f0", fg="#333333")
        self.response_text.pack(pady=2, padx=2, fill="x")

        # Verification Result
        result_frame = ttk.LabelFrame(right_frame, text="Verification Result")
        result_frame.pack(pady=5, padx=5, fill="both", expand=True)
        self.result_image_label = ttk.Label(result_frame)
        self.result_image_label.pack(pady=2, anchor="center", expand=True)
        self.result_info_label = ttk.Label(result_frame, text="", foreground="#333333")
        self.result_info_label.pack(pady=2, anchor="center", expand=True)

        self.reg_image_paths = []
        self.verify_image_path = ""

    def select_reg_images(self):
        self.reg_image_paths = filedialog.askopenfilenames(title="Select Images for Registration")
        self.reg_images_label.config(text=f"{len(self.reg_image_paths)} images selected")

    def select_verify_image(self):
        self.verify_image_path = filedialog.askopenfilename(title="Select Image for Verification")
        self.verify_image_label.config(text=os.path.basename(self.verify_image_path))

    def capture_for_verification(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Could not open camera.")
            return

        cv2.namedWindow("Capture - Press SPACE to save, ESC to exit")

        while True:
            ret, frame = cap.read()
            if not ret:
                messagebox.showerror("Error", "Failed to capture image.")
                break
            
            cv2.imshow("Capture - Press SPACE to save, ESC to exit", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == 27: # ESC
                break
            elif key == 32: # SPACE
                self.verify_image_path = "temp_verify_image.jpg"
                cv2.imwrite(self.verify_image_path, frame)
                self.verify_image_label.config(text=os.path.basename(self.verify_image_path))
                break
        
        cap.release()
        cv2.destroyAllWindows()

    def register(self):
        api_key = self.api_key_entry.get()
        person_id = self.person_id_entry.get()
        if not api_key or not person_id or not self.reg_image_paths:
            messagebox.showerror("Error", "API Key, Person ID, and at least one image are required for registration.")
            return

        headers = {"X-API-Key": api_key, "Accept": "application/json"}
        data = {"person_id": person_id}
        files = []
        for image_path in self.reg_image_paths:
            files.append(("images", (os.path.basename(image_path), open(image_path, "rb"), "image/jpeg")))

        try:
            response = requests.post("http://localhost:8800/register-upload", headers=headers, data=data, files=files)
            self.display_response(response, "register")
        except requests.exceptions.RequestException as e:
            self.display_error(e)

    def verify(self):
        api_key = self.api_key_entry.get()
        if not api_key or not self.verify_image_path:
            messagebox.showerror("Error", "API Key and an image are required for verification.")
            return

        headers = {"X-API-Key": api_key, "Accept": "application/json"}
        files = {"image": (os.path.basename(self.verify_image_path), open(self.verify_image_path, "rb"), "image/jpeg")}

        try:
            response = requests.post("http://localhost:8800/verify-upload", headers=headers, files=files)
            self.display_response(response, "verify")
        except requests.exceptions.RequestException as e:
            self.display_error(e)

    def health_check(self):
        try:
            response = requests.get("http://localhost:8800/health")
            self.display_response(response, "health")
        except requests.exceptions.RequestException as e:
            self.display_error(e)

    def delete_person(self):
        api_key = self.api_key_entry.get()
        person_id = self.person_id_entry.get()
        if not api_key or not person_id:
            messagebox.showerror("Error", "API Key and Person ID are required for deletion.")
            return

        headers = {"X-API-Key": api_key, "Accept": "application/json"}

        try:
            response = requests.delete(f"http://localhost:8800/faces/{person_id}", headers=headers)
            self.display_response(response, "delete")
        except requests.exceptions.RequestException as e:
            self.display_error(e)

    def display_response(self, response, request_type):
        self.response_text.delete(1.0, tk.END)
        self.result_image_label.config(image='')
        self.result_info_label.config(text="")

        try:
            response_json = response.json()
            if request_type == "verify" and response.status_code == 200:
                person_id = response_json.get("person_id")
                confidence = response_json.get("confidence")
                best_image_b64 = response_json.get("best_image")

                if person_id is None:
                    self.result_info_label.config(text="Face matches no registered user, please register first or try again")
                else:
                    self.result_info_label.config(text=f"Person ID: {person_id}, Confidence: {confidence:.2f}")

                if best_image_b64:
                    def fix_image_orientation(image):
                        try:
                            # Check for orientation information in EXIF data
                            for orientation in [274]:  # Orientation values from EXIF tag
                                if hasattr(image, '_getexif') and image._getexif() and orientation in image._getexif():
                                    return image.transpose(Image.Transpose.ROTATE_270)
                        except Exception:
                            pass
                        return image
                    
                    image_data = base64.b64decode(best_image_b64)
                    image = Image.open(BytesIO(image_data))
                    image = fix_image_orientation(image)
                    image.thumbnail((300, 600), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    self.result_image_label.config(image=photo)
                    self.result_image_label.image = photo
            else:
                self.response_text.insert(tk.END, f"Status Code: {response.status_code}\n\n")
                self.response_text.insert(tk.END, str(response_json))

        except requests.exceptions.JSONDecodeError:
            self.response_text.insert(tk.END, f"Status Code: {response.status_code}\n\n")
            self.response_text.insert(tk.END, response.text)

    def display_error(self, error):
        self.response_text.delete(1.0, tk.END)
        self.response_text.insert(tk.END, f"An error occurred: {error}")

if __name__ == "__main__":
    app = ApiTester()
    app.mainloop()