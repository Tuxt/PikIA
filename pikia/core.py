from InquirerPy import inquirer
from InquirerPy.validator import PathValidator
from transformers import AutoModelForCausalLM, AutoProcessor
import torch
import os
from PIL import Image

class PikIA:
    
    def __init__(self):
        self.directories = self._prompt_directories()
        self.recursive = inquirer.confirm(message="Scan directories recursively?", default=True).execute()

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
        image = Image.open(image)
        
        inputs = self.processor(text=self.prompt, images=image, return_tensors="pt").to(self.device, self.torch_dtype)
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
            return [ObjectDetection(label, bbox, image.size) for label, bbox in zip(result['labels'], result['bboxes'])]
        else:
            return result

class ObjectDetection:
    def __init__(self, tag, bbox, img_shape):
        self.tag = tag
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
        return f"ObjectDetection({self.tag}, {self.weight})"