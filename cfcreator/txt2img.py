import time

from enum import Enum
from typing import Any
from fastapi import Response
from pydantic import Field
from cfclient.utils import download_image_with_retry
from cfclient.models import ImageModel
from cfclient.models import AlgorithmBase

from .common import init_sd_ms
from .common import get_sd_from
from .common import get_sd_inpainting
from .common import handle_diffusion_model
from .common import get_bytes_from_diffusion
from .common import IAlgorithm
from .common import Txt2ImgModel


txt2img_sd_endpoint = "/txt2img/sd"
txt2img_sd_inpainting_endpoint = "/txt2img/sd.inpainting"
txt2img_sd_outpainting_endpoint = "/txt2img/sd.outpainting"


class Txt2ImgSDModel(Txt2ImgModel):
    w: int = Field(512, description="The desired output width.")
    h: int = Field(512, description="The desired output height.")
    is_anime: bool = Field(False, description="Whether should we generate anime images or not.")


@AlgorithmBase.register("txt2img.sd")
class Txt2ImgSD(IAlgorithm):
    model_class = Txt2ImgSDModel

    endpoint = txt2img_sd_endpoint

    def initialize(self) -> None:
        self.ms = init_sd_ms()

    async def run(self, data: Txt2ImgSDModel, *args: Any) -> Response:
        self.log_endpoint(data)
        t = time.time()
        size = data.w, data.h
        m = get_sd_from(self.ms, data)
        kwargs = handle_diffusion_model(m, data)
        img_arr = m.txt2img(
            data.text,
            size=size,
            max_wh=data.max_wh,
            **kwargs,
        ).numpy()[0]
        content = get_bytes_from_diffusion(img_arr)
        self.log_times({"inference": time.time() - t})
        return Response(content=content, media_type="image/png")


class PaddingModes(str, Enum):
    CV2_NS = "cv2_ns"
    CV2_TELEA = "cv2_telea"


class Txt2ImgSDInpaintingModel(Txt2ImgModel, ImageModel):
    mask_url: str = Field(
        ...,
        description="""
The `cdn` / `cos` url of the user's mask.
> `cos` url from `qcloud` is preferred.
> If empty string is provided, then we will use an empty mask, which means we will simply perform an image-to-image transform.  
""",
    )


class Txt2ImgSDOutpaintingModel(Txt2ImgModel, ImageModel):
    pass


@AlgorithmBase.register("txt2img.sd.inpainting")
class Txt2ImgSDInpainting(IAlgorithm):
    model_class = Txt2ImgSDInpaintingModel

    endpoint = txt2img_sd_inpainting_endpoint

    def initialize(self) -> None:
        self.m = get_sd_inpainting()

    async def run(self, data: Txt2ImgSDInpaintingModel, *args: Any) -> Response:
        self.log_endpoint(data)
        t0 = time.time()
        image = await download_image_with_retry(self.http_client.session, data.url)
        mask = await download_image_with_retry(self.http_client.session, data.mask_url)
        t1 = time.time()
        kwargs = handle_diffusion_model(self.m, data)
        img_arr = self.m.txt2img_inpainting(
            data.text,
            image,
            mask,
            anchor=64,
            max_wh=data.max_wh,
            **kwargs,
        ).numpy()[0]
        content = get_bytes_from_diffusion(img_arr)
        self.log_times({"download": t1 - t0, "inference": time.time() - t1})
        return Response(content=content, media_type="image/png")


@AlgorithmBase.register("txt2img.sd.outpainting")
class Txt2ImgSDOutpainting(IAlgorithm):
    model_class = Txt2ImgSDOutpaintingModel

    endpoint = txt2img_sd_outpainting_endpoint

    def initialize(self) -> None:
        self.m = get_sd_inpainting()

    async def run(self, data: Txt2ImgSDOutpaintingModel, *args: Any) -> Response:
        self.log_endpoint(data)
        t0 = time.time()
        image = await download_image_with_retry(self.http_client.session, data.url)
        t1 = time.time()
        kwargs = handle_diffusion_model(self.m, data)
        img_arr = self.m.outpainting(
            data.text,
            image,
            anchor=64,
            max_wh=data.max_wh,
            **kwargs,
        ).numpy()[0]
        content = get_bytes_from_diffusion(img_arr)
        self.log_times({"download": t1 - t0, "inference": time.time() - t1})
        return Response(content=content, media_type="image/png")


__all__ = [
    "txt2img_sd_endpoint",
    "txt2img_sd_inpainting_endpoint",
    "txt2img_sd_outpainting_endpoint",
    "Txt2ImgSDModel",
    "Txt2ImgSDInpaintingModel",
    "Txt2ImgSDOutpaintingModel",
    "Txt2ImgSD",
    "Txt2ImgSDInpainting",
    "Txt2ImgSDOutpainting",
]
