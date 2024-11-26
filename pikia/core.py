from InquirerPy import inquirer
from InquirerPy.validator import PathValidator
from transformers import AutoModelForCausalLM, AutoProcessor
import torch
import os
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from tqdm import tqdm
import db

class PikIA:

    VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".ico", ".webp"}

    def __init__(self):
        self.images = []
        self.model = Model()

    def run(self):
        # Prompt for directories
        self.directories = self._prompt_directories()

        # Directory scanning
        self.recursive = inquirer.confirm(message="Scan directories recursively?", default=True).execute()
        ready_to_scan_directories = inquirer.confirm(message="Start scan?", default=False).execute()
        
        if not ready_to_scan_directories:
            return
        
        self._scan_directories()
        if len(self.images) == 0:
            print('No images found!')
            return
        
        # Save images to db
        db.insert_imagefiles(self.images)
        
        # Image analysis
        ready_to_analyze = inquirer.confirm(message=f"{len(self.images)} found. Start analysis?", default=True).execute()
        
        if not ready_to_analyze:
            return
        
        self._analyze_and_save_images()

    def _prompt_directories(self):
        # Instructions
        print("Provide directories to scan for images")
        print("- Use arrows or tab to automplete")
        print("- Drag & Drop a directory to add")
        print("- Ctrl+C to end")

        # Prompt for directories
        directories = []
        keybindings = {
            "skip": [{"key": "c-c"}],
        }

        while True:
            new_dir = inquirer.filepath(
                message="Enter path to scan:",
                validate=PathValidator(is_dir=True, message="Input is not a directory"),
                only_directories=True,
                # FILTER NOTES
                # Need to concat `os.path.sep`: `os.path.abspath("C:")` -> `os.getcwd()`
                # Dont `os.path.join(e, os.path.sep)`: `os.path.join(".dir", os.path.sep)` -> `"\\"`
                filter=lambda e: os.path.abspath(e + os.path.sep if len(e) != 0 else ".")
                if e is not None
                else e,
                keybindings=keybindings,
                mandatory=(len(directories) == 0),
            ).execute()
            if new_dir is None:
                break
            directories.append(new_dir)
        
        # Remove duplicates
        directories = list(set(directories))

        return directories

    def _scan_directories(self):
        for directory in tqdm(self.directories):
            self._scan_directory(directory)
    
    def _scan_directory(self, directory):
        path = Path(directory)
        if self.recursive:
            self.images += [str(file) for file in path.rglob("*") if file.suffix in self.VALID_EXTENSIONS]
        else:
            self.images += [str(file) for file in path.glob("*") if file.is_file() and file.suffix in self.VALID_EXTENSIONS]

    def _analyze_and_save_images(self):
        labels = self._analyze_images()
        db.insert_analysis(labels)
    
    def _analyze_images(self):
        labels = [self.model.caption(image) for image in tqdm(self.images)]

        failed = [label.filename for label in labels if label.detections is None]
        print(f"{len(labels)} files processed")
        if len(failed) > 0:
            print(f"{len(failed)} invalid images:")
            for filename in failed:
                print(f"> {filename}")
        return labels


class Model:
    
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    def __init__(self, model="microsoft/Florence-2-large", prompt="<OD>"):
        self.prompt = prompt # "<CAPTION>" | "<DETAILED_CAPTION>" | "<MORE_DETAILED_CAPTION>" | "<OD>"
        
        # Initialize model
        self.model = AutoModelForCausalLM.from_pretrained(
            model, torch_dtype=self.torch_dtype, trust_remote_code=True
        ).to(self.device)
        self.processor = AutoProcessor.from_pretrained(model, trust_remote_code=True)

    def caption(self, image):
        try:
            image = Image.open(image)
        except (FileNotFoundError, UnidentifiedImageError):
            return ImageAnalysis(image, None)
        
        inputs = self.processor(text=self.prompt, images=image.convert("RGB"), return_tensors="pt").to(self.device, self.torch_dtype)
        generated_ids = self.model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            num_beams=3,
        )
        generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=False)[0]

        parsed_answer = self.processor.post_process_generation(
            generated_text, task=self.prompt, image_size=image.size
        )
        image.close()
        
        result = parsed_answer[self.prompt]
        if self.prompt == '<OD>':
            img_analysis = ImageAnalysis(image.filename, [ObjectDetection(label, bbox, image.size) for label, bbox in zip(result['labels'], result['bboxes'])])
            return img_analysis
        else:
            return result


class ObjectDetection:
    def __init__(self, label, bbox, img_shape):
        self.label = label
        self.img_shape = img_shape
        self.bbox = bbox
    
    @property
    def img_shape(self):
        return self._img_shape

    @img_shape.setter
    def img_shape(self, value):
        self._img_shape = value
        self.img_area = self.calc_area((0, 0, *value))
        self.max_img_distance = self.calc_point_distance((0, 0), value)

    @property
    def bbox(self):
        return self._bbox

    @bbox.setter
    def bbox(self, bbox):
        self._bbox = bbox
        self.calc_weight()


    def calc_weight(self):
        self.calc_area_weight()
        self.calc_centrality_weight()
        self.weight = self.area_weight * self.centrality_weight
    
    def calc_area_weight(self):
        bbox_area = self.calc_area(self._bbox)
        self.area_weight = bbox_area / self.img_area
    
    def calc_centrality_weight(self):
        self.bbox_distance = ObjectDetection.calc_bbox_distance(
            self.bbox, (0, 0, *self.img_shape)
        )
        self.centrality_weight = 1 - (self.bbox_distance / self.max_img_distance)
        
    def normalize_weight(self, max_weight):
        self.normalized_weight = self.weight / max_weight

    @staticmethod
    def calc_area(bbox):
        x1, y1, x2, y2 = bbox
        return (x2 - x1) * (y2 - y1)

    @staticmethod
    def calc_center(bbox):
        x1, y1, x2, y2 = bbox
        return ((x2 + x1) / 2 , (y2 + y1) / 2)

    @staticmethod
    def calc_point_distance(p1, p2):
        x1, y1 = p1
        x2, y2 = p2
        return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
    
    @staticmethod
    def calc_bbox_distance(bbox1, bbox2):
        p1 = ObjectDetection.calc_center(bbox1)
        p2 = ObjectDetection.calc_center(bbox2)
        return ObjectDetection.calc_point_distance(p1, p2)

    def __str__(self):
        return f"ObjectDetection({self.label}, {self.weight})"


class ImageAnalysis:
    def __init__(self, filename: str, detections: list[ObjectDetection] | None):
        self.filename = filename
        self.detections = sorted(detections, key=lambda x: x.weight, reverse=True) if detections is not None else None
        self._cache = {}
    
    def get_top_detections(self, method: str = "top_n", n: int = 3):
        # Check for None detections
        if self.detections is None:
            return []
        
        # Check cache
        cache_key = (method, n)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if method == "top_n":
            result = self.detections[:n]
        elif method == "relative_threshold":
            total_weight = sum(d.weight for d in self.detections)
            acc = 0
            top_detections = []
            for detection in self.detections:
                detection.normalize_weight(total_weight)
                acc += detection.normalized_weight
                top_detections.append(detection)
                if acc >= 0.8:
                    break
            
            result = top_detections
        
        self._cache[cache_key] = result
        return result
            
