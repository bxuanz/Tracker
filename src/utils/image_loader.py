import numpy as np
import rasterio
from PIL import Image

MAX_TEXTURE_SIZE = 8192 

class ImageLoader:
    @staticmethod
    def load(path):
        """
        通用图像加载器
        返回: (image_data_uint8, scale_factor, original_size_tuple)
        image_data_uint8: (H, W, C) 格式的 numpy 数组
        """
        if path.lower().endswith(('.tif', '.tiff')):
            return ImageLoader._load_geotiff(path)
        else:
            return ImageLoader._load_standard_image(path)

    @staticmethod
    def _load_geotiff(path):
        try:
            with rasterio.open(path) as src:
                orig_w, orig_h = src.width, src.height
                max_dim = max(orig_w, orig_h)
                scale = MAX_TEXTURE_SIZE / max_dim if max_dim > MAX_TEXTURE_SIZE else 1.0
                target_w, target_h = int(orig_w * scale), int(orig_h * scale)
                
                # 读取并重采样
                if src.count >= 3:
                    img_data = src.read([1, 2, 3], out_shape=(3, target_h, target_w))
                    img_data = np.transpose(img_data, (1, 2, 0)) # (H, W, C)
                else:
                    img_data = src.read(1, out_shape=(1, target_h, target_w))
                    img_data = np.stack([img_data]*3, axis=-1)

                # 简单的对比度拉伸 (去除极值)
                p2, p98 = np.percentile(img_data, 2), np.percentile(img_data, 98)
                img_data = np.clip((img_data - p2) / (p98 - p2 + 1e-6) * 255, 0, 255).astype(np.uint8)
                
                if not img_data.flags['C_CONTIGUOUS']:
                    img_data = np.ascontiguousarray(img_data)
                    
                return img_data, scale, (orig_w, orig_h)
        except Exception as e:
            print(f"GeoTIFF Load Error: {e}")
            return None, 1.0, (0, 0)

    @staticmethod
    def _load_standard_image(path):
        try:
            # 使用 Pillow 加载普通图片
            with Image.open(path) as img:
                img = img.convert('RGB') # 确保是3通道
                orig_w, orig_h = img.size
                
                # 依然应用最大尺寸限制，防止超大PNG卡顿
                max_dim = max(orig_w, orig_h)
                scale = MAX_TEXTURE_SIZE / max_dim if max_dim > MAX_TEXTURE_SIZE else 1.0
                
                if scale < 1.0:
                    target_w, target_h = int(orig_w * scale), int(orig_h * scale)
                    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                
                img_data = np.array(img).astype(np.uint8)
                return img_data, scale, (orig_w, orig_h)
        except Exception as e:
            print(f"Standard Image Load Error: {e}")
            return None, 1.0, (0, 0)