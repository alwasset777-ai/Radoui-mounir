# -*- coding: utf-8 -*-
"""
✨ فيديو بالذكاء الاصطناعي — نسخة شخصية فابور 100% (بلا جواهر، بلا اشتراك)
- صورة إلى فيديو  /  نص إلى فيديو
- الموديل: Wan 2.2 TI2V-5B (مفتوح، رخصة Apache 2.0) على GPU فابور ديال Kaggle
- المدة الطويلة: قطع ديال 5 ثواني كتتلصق (كل قطعة كتبدا من آخر لقطة ديال اللي قبلها)
- الرابط الثابت: كيتصيفط أوتوماتيكياً لصفحة ntfy (إشعار فالتليفون)
"""
import os
import re
import sys
import time
import uuid
import queue
import random
import shutil
import datetime
import json
import threading
import traceback
import subprocess

import numpy as np
from PIL import Image, ImageOps

# ----------------------------------------------------------------------------
# الإعدادات
# ----------------------------------------------------------------------------
MODEL_ID = os.environ.get("WAN_MODEL_ID", "Wan-AI/Wan2.2-TI2V-5B-Diffusers")
ON_KAGGLE = os.path.isdir("/kaggle/working")
OUT_DIR = os.environ.get(
    "VIDEO_OUT_DIR", "/kaggle/working/videos" if ON_KAGGLE else os.path.abspath("videos")
)
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
IDLE_MINUTES = float(os.environ.get("IDLE_MINUTES", "60"))  # كيطفى بوحدو إلا بقى خاوي باش توفر الساعات
PORT = int(os.environ.get("PORT", "7860"))
FPS = 24
SEG_FRAMES = int(os.environ.get("SEG_FRAMES", "121"))  # 121 لقطة = 5 ثواني
SEG_SECONDS = (SEG_FRAMES - 1) / FPS
MAX_SEQ = 512
DURATIONS = [5, 10, 15, 20, 30, 45, 60]

ASPECTS = ["عمودي 9:16", "أفقي 16:9", "مربع 1:1"]
Q_HIGH, Q_FAST = "عالية (720p)", "سريعة (480p)"
QUALITY = {
    Q_HIGH: {
        "area": 704 * 1280,
        "steps": 35,
        "sizes": {"عمودي 9:16": (704, 1280), "أفقي 16:9": (1280, 704), "مربع 1:1": (960, 960)},
    },
    Q_FAST: {
        "area": 480 * 832,
        "steps": 30,
        "sizes": {"عمودي 9:16": (480, 832), "أفقي 16:9": (832, 480), "مربع 1:1": (640, 640)},
    },
}
MOD = 32

NEG_PROMPT = (
    "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，"
    "JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，"
    "形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走，"
    "裸露，色情，nsfw, nudity"
)
DEFAULT_PROMPT = "Natural smooth motion, gentle cinematic camera movement, realistic lighting, high quality, detailed"
NO_GPU_MSG = "❌ ما كاينش GPU. فـ Kaggle: Settings ← Accelerator ← «GPU T4 x2»، ومن بعد عاود."

STATE = {"url": None, "last_activity": time.time()}


def log(*a):
    print(datetime.datetime.now().strftime("%H:%M:%S"), *a, flush=True)


def touch():
    STATE["last_activity"] = time.time()


# ----------------------------------------------------------------------------
# إشعارات فالتليفون (ntfy.sh — فابور بلا حساب)
# ----------------------------------------------------------------------------
def notify(title, message, click=None, tags=None, priority=3):
    if not NTFY_TOPIC:
        return False
    body = {"topic": NTFY_TOPIC, "title": title, "message": message, "priority": priority, "tags": tags or []}
    if click:
        body["click"] = click
        body["actions"] = [{"action": "view", "label": "افتح التطبيق", "url": click}]
    try:
        import requests

        r = requests.post(os.environ.get("NTFY_SERVER", "https://ntfy.sh/"), json=body, timeout=15)
        return r.ok
    except Exception as e:
        log("notify failed:", e)
        return False


# ----------------------------------------------------------------------------
# أدوات صغيرة
# ----------------------------------------------------------------------------
def size_from_image(img, area):
    ratio = img.height / img.width
    h = int(round(np.sqrt(area * ratio)) // MOD * MOD)
    w = int(round(np.sqrt(area / ratio)) // MOD * MOD)
    return max(MOD, w), max(MOD, h)


def fit_image(img, w, h):
    return ImageOps.fit(img.convert("RGB"), (w, h), method=Image.LANCZOS, centering=(0.5, 0.5))


def match_color(img, ref, strength=0.5):
    try:
        import cv2
    except ImportError:
        return img
    a = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2LAB).astype(np.float32)
    r = cv2.cvtColor(np.asarray(ref.convert("RGB")), cv2.COLOR_RGB2LAB).astype(np.float32)
    am, asd = a.reshape(-1, 3).mean(0), a.reshape(-1, 3).std(0) + 1e-5
    rm, rsd = r.reshape(-1, 3).mean(0), r.reshape(-1, 3).std(0) + 1e-5
    out = (a - am) / asd * rsd + rm
    out = np.clip(a * (1 - strength) + out * strength, 0, 255).astype(np.uint8)
    return Image.fromarray(cv2.cvtColor(out, cv2.COLOR_LAB2RGB))


_tr_cache = {}


def to_english(text):
    if not re.search(r"[؀-ۿ]", text):
        return text
    if text in _tr_cache:
        return _tr_cache[text]
    try:
        from deep_translator import GoogleTranslator

        out = GoogleTranslator(source="auto", target="en").translate(text) or text
    except Exception as e:
        log("translation failed:", e)
        out = text
    _tr_cache[text] = out
    return out


def ffmpeg_exe():
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"


def write_mp4(frames_u8, path):
    import imageio.v2 as imageio

    w = imageio.get_writer(path, fps=FPS, codec="libx264", quality=8, pixelformat="yuv420p",
                           macro_block_size=1, ffmpeg_log_level="error")
    for f in frames_u8:
        w.append_data(f)
    w.close()


def concat_mp4(parts, out_path):
    if len(parts) == 1:
        shutil.copyfile(parts[0], out_path)
        return
    lst = out_path + ".txt"
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")
    tmp = out_path + ".tmp.mp4"
    subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", tmp], check=True)
    os.replace(tmp, out_path)
    os.remove(lst)


class Cancelled(Exception):
    pass


# ----------------------------------------------------------------------------
# المحرك
# ----------------------------------------------------------------------------
class Engine:
    def __init__(self):
        self.ready = False
        self.error = None
        self.status = "⏳ كيتوجد…"
        self._active = None
        self._emb = {}
        self.cuda = False

    def load(self, components=None):
        try:
            import torch
            from diffusers import WanImageToVideoPipeline, WanPipeline

            self.torch = torch
            self.t_load = time.time()
            if components is None:
                if not torch.cuda.is_available():
                    raise RuntimeError(NO_GPU_MSG)
                from diffusers import AutoencoderKLWan, UniPCMultistepScheduler, WanTransformer3DModel
                from transformers import AutoTokenizer, UMT5EncoderModel

                n_gpu = torch.cuda.device_count()
                self.status = "⏳ كنحمّل الموديل (أول مرة 5 حتى 15 دقيقة)…"
                log(self.status, f"GPUs={n_gpu}")
                tok = AutoTokenizer.from_pretrained(MODEL_ID, subfolder="tokenizer")
                # فهم النص: إلا كاين جوج GPU كنحطوه فالثاني (أسرع ويخفف الذاكرة)، وإلا فالـ CPU
                if n_gpu >= 2:
                    te = UMT5EncoderModel.from_pretrained(MODEL_ID, subfolder="text_encoder",
                                                          torch_dtype=torch.float16).to("cuda:1")
                else:
                    te = UMT5EncoderModel.from_pretrained(MODEL_ID, subfolder="text_encoder",
                                                          torch_dtype=torch.bfloat16)
                self.status = "⏳ كنحمّل الجزء الكبير ديال الموديل…"
                tr = WanTransformer3DModel.from_pretrained(MODEL_ID, subfolder="transformer", torch_dtype=torch.float16)
                vae = AutoencoderKLWan.from_pretrained(MODEL_ID, subfolder="vae", torch_dtype=torch.float32)
                sch = UniPCMultistepScheduler.from_pretrained(MODEL_ID, subfolder="scheduler")
                components = dict(tokenizer=tok, text_encoder=te, transformer=tr, vae=vae, scheduler=sch)

            self.tokenizer = components["tokenizer"]
            self.text_encoder = components["text_encoder"].eval()
            self.vae = components["vae"]
            common = dict(
                tokenizer=components["tokenizer"], text_encoder=None, vae=components["vae"],
                scheduler=components["scheduler"], transformer=components["transformer"],
                transformer_2=None, boundary_ratio=None, expand_timesteps=True,
            )
            self.i2v = WanImageToVideoPipeline(image_processor=None, image_encoder=None, **common)
            _orig_prepare = self.i2v.prepare_latents

            def _prepare_then_free_vae(*a, **k):
                out = _orig_prepare(*a, **k)
                if torch.cuda.is_available():
                    self.vae.to("cpu")  # كيرجع بوحدو للـ GPU ملي نحتاجوه فالأخير
                    torch.cuda.empty_cache()
                return out

            self.i2v.prepare_latents = _prepare_then_free_vae
            self.t2v = WanPipeline(**common)
            for p in (self.i2v, self.t2v):
                p.set_progress_bar_config(disable=True)
            self.cuda = torch.cuda.is_available()
            self.embed(NEG_PROMPT)  # كنجربو فهم النص من دابا
            self.status = "⏳ كنجرب الموديل بفيديو صغير…"
            self.self_test()
            self.ready = True
            touch()  # عداد الإطفاء كيبدا من دابا، ماشي من وقت التحميل
            self.status = "✅ واجد"
            log("model ready")
            notify("✅ التطبيق واجد", "الموديل تحمّل، تقدر تصاوب الفيديوهات دابا.", STATE["url"], ["white_check_mark"])
        except Exception as e:
            self.error = str(e)
            self.status = f"❌ مشكل فتحميل الموديل: {e}"
            log(self.status)
            traceback.print_exc()
            notify("❌ مشكل فالتطبيق", self.status[:300], None, ["x"], 4)

    def _encode(self, text):
        torch = self.torch
        from diffusers.pipelines.wan.pipeline_wan import prompt_clean

        dev = next(self.text_encoder.parameters()).device
        inputs = self.tokenizer([prompt_clean(text)], padding="longest", max_length=MAX_SEQ, truncation=True,
                                add_special_tokens=True, return_attention_mask=True, return_tensors="pt")
        with torch.no_grad():
            h = self.text_encoder(inputs.input_ids.to(dev), inputs.attention_mask.to(dev)).last_hidden_state
        n = int(inputs.attention_mask.gt(0).sum())
        return h[0, :n].float().cpu()

    def embed(self, text):
        torch = self.torch
        if text in self._emb:
            return self._emb[text]
        h = self._encode(text)
        if not torch.isfinite(h).all():  # احتياط: إلا فشل فالـ GPU كنرجعو للـ CPU
            log("text encoder gave NaN → moving to CPU bf16")
            self.text_encoder = self.text_encoder.to("cpu", torch.bfloat16)
            h = self._encode(text)
        h = torch.cat([h, h.new_zeros(MAX_SEQ - h.size(0), h.size(1))])[None]
        self._emb[text] = h
        return h

    def _use(self, pipe):
        if self.cuda and self._active is not pipe:
            pipe.enable_model_cpu_offload(gpu_id=0)
            self._active = pipe

    def _decode(self, latents):
        torch = self.torch
        from diffusers.utils.torch_utils import get_module_execution_device

        vae = self.vae
        lat = latents.to(device=get_module_execution_device(vae), dtype=vae.dtype)
        mean = torch.tensor(vae.config.latents_mean).view(1, vae.config.z_dim, 1, 1, 1).to(lat.device, lat.dtype)
        std = 1.0 / torch.tensor(vae.config.latents_std).view(1, vae.config.z_dim, 1, 1, 1).to(lat.device, lat.dtype)
        lat = lat / std + mean
        with torch.no_grad():
            try:
                video = vae.decode(lat, return_dict=False)[0]
            except torch.cuda.OutOfMemoryError:
                log("decode OOM → retry with tiling")
                torch.cuda.empty_cache()
                vae.enable_tiling()
                video = vae.decode(lat, return_dict=False)[0]
        frames = self.i2v.video_processor.postprocess_video(video, output_type="np")[0]
        return (np.clip(frames, 0, 1) * 255).round().astype(np.uint8)

    def to_bf16(self):
        """إلا الموديل عطى نتيجة خاوية (NaN) بدقة fp16، كنبدلوه لـ bf16 (أبطأ شوية ولكن أضمن)."""
        torch = self.torch
        tr = self.i2v.transformer
        if tr.dtype == torch.bfloat16:
            return False
        log("fp16 gave NaN → switching transformer to bf16")
        for p in (self.i2v, self.t2v):
            try:
                p.remove_all_hooks()
            except Exception:
                pass
        # نفس القاعدة ديال diffusers: شي أجزاء حساسة كتبقى بدقة كاملة (float32)
        keep = getattr(tr, "_keep_in_fp32_modules", None) or []
        with torch.no_grad():
            for name, t in list(tr.named_parameters()) + list(tr.named_buffers()):
                if t.is_floating_point():
                    t.data = t.data.float() if any(m in name for m in keep) else t.data.to(torch.bfloat16)
        self._active = None
        if self.cuda:
            torch.cuda.empty_cache()
        return True

    def self_test(self):
        """فيديو صغير (9 لقطات) كنتأكدو بيه بلي كلشي خدام قبل ما نقولو «واجد»."""
        for attempt in range(2):
            try:
                frames = self.segment(DEFAULT_PROMPT, None, 256, 256, 2, 5.0, 0, lambda s: None, num_frames=9)
                assert frames.shape[0] == 9
                log("self-test OK", frames.shape)
                return
            except RuntimeError as e:
                if "NAN_RESULT" in str(e) and attempt == 0 and self.to_bf16():
                    continue
                raise

    def segment(self, prompt_en, image, w, h, steps, guidance, seed, on_step, num_frames=None):
        torch = self.torch
        pipe = self.t2v if image is None else self.i2v
        self._use(pipe)
        dev = pipe._execution_device
        dt = pipe.transformer.dtype
        pe = self.embed(prompt_en).to(dev, dt)
        ne = self.embed(NEG_PROMPT).to(dev, dt)

        def cb(p, i, t, kw):
            on_step(i + 1)
            return kw

        kwargs = dict(
            prompt_embeds=pe, negative_prompt_embeds=ne, height=h, width=w, num_frames=num_frames or SEG_FRAMES,
            num_inference_steps=steps, guidance_scale=guidance,
            generator=torch.Generator(device="cpu").manual_seed(int(seed)),
            output_type="latent", callback_on_step_end=cb,
        )
        if image is not None:
            kwargs["image"] = image
        with torch.no_grad():
            latents = pipe(**kwargs).frames
        if not torch.isfinite(latents).all():
            raise RuntimeError("NAN_RESULT")
        frames = self._decode(latents)
        if self.cuda:
            torch.cuda.empty_cache()
        return frames


ENGINE = Engine()


# ----------------------------------------------------------------------------
# الطلبات (كتخدم فالخلفية)
# ----------------------------------------------------------------------------
class Job:
    def __init__(self, **kw):
        self.id = datetime.datetime.now().strftime("%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self.__dict__.update(kw)
        self.state = "queued"
        self.seg_i = 0
        self.step = 0
        self.msg = "فاللائحة…"
        self.out = None
        self.cancel = False
        self.sec_per_step = None
        self.done_steps = 0
        self.frame_i = 0          # تقدم تبديل الوجوه (كيتعمرو قبل ما يبدا الخدمة باش ما يطيحش العرض)
        self.frames_total = 0
        self.t_swap = time.time()


JOBS = []
LAST = {}  # آخر إعدادات تصيفطو (باش نعاودو بيهم)
Q = queue.Queue()


def run_job(job):
    job.state = "running"
    folder = os.path.join(OUT_DIR, "parts", job.id)
    os.makedirs(folder, exist_ok=True)
    final = os.path.join(OUT_DIR, f"video_{job.id}.mp4")
    parts = []
    q = QUALITY[job.quality]
    image = None
    if job.image is not None:
        img = ImageOps.exif_transpose(job.image).convert("RGB")
        w, h = size_from_image(img, q["area"])
        image = fit_image(img, w, h)
    else:
        w, h = q["sizes"][job.aspect]
    first_frame = image
    prompts_en = [to_english(p) if job.translate else p for p in job.prompts]
    if getattr(job, "kind", "gen") == "face_ai":
        prompts_en = [p + FACE_SUFFIX for p in prompts_en]
    job.w, job.h = w, h
    denoise_time = 0.0

    for i in range(job.n_seg):
        if job.cancel:
            raise Cancelled()
        job.seg_i = i + 1
        job.step = 0
        prompt = prompts_en[min(i, len(prompts_en) - 1)]
        if getattr(job, "kind", "gen") == "story" and (i == 0 or not getattr(job, "chain", True)):
            image = story_start(job, i, w, h)
        job.msg = f"كنصاوب القطعة {i + 1} من {job.n_seg}"
        log(f"[{job.id}] seg {i + 1}/{job.n_seg} {w}x{h} prompt={prompt[:80]!r}")
        t_seg = time.time()

        def on_step(s, _t=[time.time()]):
            nonlocal denoise_time
            if job.cancel:
                raise Cancelled()
            now = time.time()
            if s > 1:
                denoise_time += now - _t[0]
                job.done_steps += 1
                job.sec_per_step = denoise_time / job.done_steps
            _t[0] = now
            job.step = s

        try:
            frames = ENGINE.segment(prompt, image, w, h, job.steps, job.guidance, job.seed + i, on_step)
        except RuntimeError as e:
            if "NAN_RESULT" not in str(e) or not ENGINE.to_bf16():
                raise
            job.msg = f"كنعاود القطعة {i + 1} بدقة أخرى…"
            frames = ENGINE.segment(prompt, image, w, h, job.steps, job.guidance, job.seed + i, on_step)
        job.extra_per_seg = time.time() - t_seg - (job.sec_per_step or 0) * job.steps
        if getattr(job, "kind", "gen") == "story" and FACES.ready:
            for fr in (frames[0], frames[len(frames) // 2], frames[-1]):
                if FACES.nsfw_score(np.ascontiguousarray(fr[:, :, ::-1])) > NSFW_LIMIT:
                    shutil.rmtree(folder, ignore_errors=True)
                    if os.path.exists(final):
                        os.remove(final)
                    job.out = None
                    raise PermissionError(NSFW_MSG)
        if first_frame is None:
            first_frame = Image.fromarray(frames[0])
        last = Image.fromarray(frames[-1])
        part = os.path.join(folder, f"part_{i + 1:02d}.mp4")
        write_mp4(frames if i == 0 else frames[1:], part)
        parts.append(part)
        concat_mp4(parts, final)
        job.out = final
        if getattr(job, "chain", True):  # «لقطات منفصلة» فالقصة: كل سطر كيبدا من الصفر
            image = match_color(last, first_frame, 0.5) if job.colorfix else last
        del frames

    job.state = "done"
    job.msg = f"✅ الفيديو واجد (رقم البذرة: {job.seed})"
    shutil.rmtree(folder, ignore_errors=True)


def worker():
    while True:
        job = Q.get()
        if job.cancel:
            job.state, job.msg = "cancelled", "⏹️ تلغى"
            continue
        while not ENGINE.ready and ENGINE.error is None:
            job.msg = "كنتسناو الموديل يتحمّل…"
            time.sleep(2)
        if ENGINE.error:
            job.state, job.msg = "error", ENGINE.status
            continue
        try:
            kind = getattr(job, "kind", "gen")
            job.note = ""
            if kind == "swap":
                job.state, job.msg = "running", "🔄 كنبدل الوجوه…"
                run_swap(job, job.video)
                job.state, job.msg = "done", ("✅ الوجوه تبدلو " + job.note).strip()
                notify("🎭 الفيديو واجد", "الوجوه تبدلو. دخل حمّل الفيديو.", STATE["url"], ["performing_arts"], 4)
                touch()
                log(f"[{job.id}] {job.state}: {job.msg}")
                continue
            if kind == "avatar":
                job.state = "running"
                run_avatar(job)
                touch()
                log(f"[{job.id}] {job.state}: {job.msg}")
                continue
            if kind == "story" and not FACES.ready:
                FACES.load()
            try:
                run_job(job)
            except Exception as e:
                if not is_oom(e) or job.quality == Q_FAST:
                    raise
                log(f"[{job.id}] OOM at {job.quality} → retry at {Q_FAST}")
                free_gpu()
                job.quality, job.steps = Q_FAST, min(job.steps, QUALITY[Q_FAST]["steps"])
                job.seg_i = job.step = job.done_steps = 0
                job.sec_per_step, job.out = None, None
                job.note = "ℹ️ الجودة العالية ما دخلاتش فالذاكرة، تصاوب بالسريعة."
                run_job(job)
            if kind in ("face_ai", "story") and getattr(job, "sources", None):
                gen_msg = job.msg
                job.state, job.msg = "running", ("🎭 كنحط الوجه ديالك فالفيديو…" if kind == "face_ai"
                                                 else "👤 كنثبت الوجه ديال الشخصية فجميع اللقطات…")
                gen_path = job.out
                run_swap(job, gen_path, all_faces=True if kind == "face_ai" else "largest")
                try:
                    os.remove(gen_path)  # كنخليو غير الفيديو النهائي بالوجه
                except OSError:
                    pass
                job.state, job.msg = "done", gen_msg.replace(
                    "الفيديو واجد", "الفيديو بالوجه ديالك واجد" if kind == "face_ai" else "القصة واجدة")
            elif kind == "story":
                job.msg = job.msg.replace("الفيديو واجد", "القصة واجدة")
            if job.note:
                job.msg += " " + job.note
            notify("🎬 الفيديو واجد", f"فيديو ديال {job.n_seg * 5} ثانية تصاوب. دخل حمّلو.", STATE["url"], ["clapper"], 4)
        except PermissionError as e:
            job.state, job.msg = "error", str(e)
        except Cancelled:
            job.state = "cancelled"
            job.msg = "⏹️ توقف" + (" — الجزء اللي تصاوب محفوظ" if job.out else "")
        except Exception as e:
            job.state = "error"
            s = str(e)
            if is_oom(e):
                job.msg = "❌ الذاكرة ما كفاتش. اختار الجودة «سريعة» وعاود."
            elif "NAN_RESULT" in s:
                job.msg = "❌ النتيجة خرجات خاوية. عاود بـ «رقم البذرة» آخر ولا بالجودة «سريعة»."
            else:
                job.msg = f"❌ وقع مشكل: {e}"
            traceback.print_exc()
            notify("❌ الفيديو ما تصاوبش", job.msg, STATE["url"], ["x"])
            free_gpu()
        touch()
        log(f"[{job.id}] {job.state}: {job.msg}")


def is_oom(e):
    return "out of memory" in str(e).lower() or type(e).__name__ == "OutOfMemoryError"


def free_gpu():
    try:
        ENGINE.vae.to("cpu")
        ENGINE.torch.cuda.empty_cache()
    except Exception:
        pass


def busy():
    return any(j.state in ("queued", "running") for j in JOBS)


def shutdown(reason):
    log("shutdown:", reason)
    notify("🔌 التطبيق طفا", reason + " الفيديوهات محفوظين فـ Output ديال Kaggle.\n"
           "باش تعاود تشعلو: Kaggle ← النوتبوك ديالك ← Save Version ← Save & Run All.",
           "https://www.kaggle.com/code", ["electric_plug"])
    time.sleep(1)
    os._exit(0)


def idle_watchdog():
    while True:
        time.sleep(30)
        if IDLE_MINUTES > 0 and not busy() and time.time() - STATE["last_activity"] > IDLE_MINUTES * 60:
            shutdown(f"ما تستعملش {int(IDLE_MINUTES)} دقيقة، طفيتو باش توفر الساعات ديال GPU.")


def fmt_min(sec):
    if sec is None:
        return "كيتحسب…"
    m = int(round(sec / 60))
    if m < 1:
        return "أقل من دقيقة"
    if m < 60:
        return f"{m} دقيقة"
    return f"{m // 60} ساعة و{m % 60} دقيقة"


def eta(job):
    if getattr(job, "phase", "gen") == "swap":
        if job.state != "running" or job.frame_i < 10:
            return None
        return (time.time() - job.t_swap) / job.frame_i * (job.frames_total - job.frame_i)
    if job.state != "running" or not job.sec_per_step:
        return None
    remaining_steps = (job.n_seg - job.seg_i) * job.steps + (job.steps - job.step)
    return remaining_steps * job.sec_per_step + (job.n_seg - job.seg_i + 1) * max(0, getattr(job, "extra_per_seg", 30))


# ----------------------------------------------------------------------------
# 🎭 تبديل الوجوه (فيديو + صور) و«وجهي فـ فيديو AI»
# ----------------------------------------------------------------------------
FACE_ROOT = os.path.expanduser(os.environ.get("FACE_MODELS", "~/.face_models"))
_FF = "https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/"
FACE_FILES = {
    "buffalo_l.zip": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip",
    "inswapper_128_fp16.onnx": _FF + "inswapper_128_fp16.onnx",
    "gfpgan_1.4.onnx": _FF + "gfpgan_1.4.onnx",
    "open_nsfw.onnx": _FF + "open_nsfw.onnx",
}
MAX_CHARS = 6
MAX_SWAP_SECONDS = int(os.environ.get("MAX_SWAP_SECONDS", "300"))  # حتى 5 دقايق ديال الفيديو
MAX_SIDE = int(os.environ.get("SWAP_MAX_SIDE", "1920"))
NSFW_LIMIT = 0.8
CLUSTER_SIM, MATCH_SIM = 0.40, 0.30
FACE_SUFFIX = ", a single person, face clearly visible, looking towards the camera, natural light, sharp details"
CONSENT_MSG = "⚠️ خاصك تأكد بلي عندك الإذن ديال الناس اللي فالصور والفيديو (المربع ✅)."
NSFW_MSG = "⛔ هاد المحتوى فيه صور ديال الكبار (+18). التطبيق ما كيبدلش الوجوه فهاد النوع."
# المكان ديال العينين والأنف والفم فوجه مقاد 512×512 (FFHQ) — باش نوضحو الوجه
FFHQ_512 = np.array([[0.37691676, 0.46864664], [0.62285697, 0.46912813], [0.50123859, 0.61331904],
                     [0.39308822, 0.72541100], [0.61150205, 0.72490465]], dtype=np.float32) * 512


def ensure_face_deps():
    """كنثبتو أدوات الوجوه أوتوماتيكياً إلا ما كانوش (بلا ما تبدل النوتبوك)."""
    try:
        import insightface  # noqa: F401
        import onnxruntime  # noqa: F401
        return
    except ImportError:
        pass
    log("installing face tools…")
    gpu = shutil.which("nvidia-smi") is not None
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "onnxruntime-gpu" if gpu else "onnxruntime",
                    "onnx", "scikit-image"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-deps", "insightface==2.1"], check=True)
    import importlib
    importlib.invalidate_caches()


class FaceTools:
    def __init__(self):
        self.ready = False
        self.error = None
        self.status = "⏳ مازال ما تحمّلوش"
        self._lock = threading.Lock()
        self.providers = []

    def load(self):
        with self._lock:
            if self.ready:
                return True
            try:
                self.status = "⏳ كنجهز أدوات الوجوه (أول مرة شي دقيقة)…"
                ensure_face_deps()
                import urllib.request
                import zipfile

                import onnxruntime as ort
                try:
                    import torch  # كيخلي onnxruntime يلقى مكتبات CUDA
                    n_gpu = torch.cuda.device_count()
                except Exception:
                    n_gpu = 0
                try:
                    ort.preload_dlls()
                except Exception:
                    pass
                os.makedirs(FACE_ROOT, exist_ok=True)
                for name, url in FACE_FILES.items():
                    dst = os.path.join(FACE_ROOT, name)
                    if not os.path.exists(dst):
                        log("downloading", name)
                        urllib.request.urlretrieve(url, dst + ".part")
                        os.replace(dst + ".part", dst)
                bdir = os.path.join(FACE_ROOT, "models", "buffalo_l")
                if not os.path.exists(os.path.join(bdir, "w600k_r50.onnx")):
                    os.makedirs(bdir, exist_ok=True)
                    with zipfile.ZipFile(os.path.join(FACE_ROOT, "buffalo_l.zip")) as z:
                        z.extractall(bdir)
                dev = 1 if n_gpu >= 2 else 0  # الكارت الثانية باش ما نزاحموش موديل الفيديو
                use_gpu = "CUDAExecutionProvider" in ort.get_available_providers() and n_gpu > 0
                prov = [("CUDAExecutionProvider", {"device_id": dev}), "CPUExecutionProvider"] if use_gpu \
                    else ["CPUExecutionProvider"]
                import insightface
                from insightface.app import FaceAnalysis

                self.app = FaceAnalysis(name="buffalo_l", root=FACE_ROOT, allowed_modules=["detection", "recognition"],
                                        providers=prov)
                self.app.prepare(ctx_id=dev if use_gpu else -1, det_size=(640, 640))
                self.swapper = insightface.model_zoo.get_model(os.path.join(FACE_ROOT, "inswapper_128_fp16.onnx"),
                                                               providers=prov)
                self.enh = ort.InferenceSession(os.path.join(FACE_ROOT, "gfpgan_1.4.onnx"), providers=prov)
                self.nsfw = ort.InferenceSession(os.path.join(FACE_ROOT, "open_nsfw.onnx"), providers=prov)
                self.providers = self.enh.get_providers()
                self.ready = True
                self.error = None
                self.status = "✅ واجدين" + (" (GPU)" if "CUDAExecutionProvider" in self.providers else " (CPU — بطيء شوية)")
                log("face tools ready", self.providers)
                return True
            except Exception as e:
                self.error = str(e)
                self.status = f"❌ مشكل فأدوات الوجوه: {e}"
                traceback.print_exc()
                return False

    # --- أدوات صغيرة ---
    def faces(self, bgr):
        return [f for f in self.app.get(bgr) if float(f.det_score) >= 0.5]

    def best_face(self, pil_img):
        import cv2

        bgr = cv2.cvtColor(np.asarray(ImageOps.exif_transpose(pil_img).convert("RGB")), cv2.COLOR_RGB2BGR)
        fs = self.faces(bgr)
        if not fs:
            return None, bgr
        return max(fs, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])), bgr

    def nsfw_score(self, bgr):
        import cv2

        x = cv2.resize(bgr, (224, 224)).astype(np.float32) - np.array([104, 117, 123], np.float32)
        return float(self.nsfw.run(None, {"input": x[None]})[0][0][1])

    def enhance(self, bgr, kps, strength=0.8):
        """كنوضحو الوجه (GFPGAN) ونرجعوه لبلاصتو بحواشي ناعمين."""
        import cv2

        M = cv2.estimateAffinePartial2D(np.asarray(kps, np.float32), FFHQ_512, method=cv2.LMEDS)[0]
        if M is None:
            return bgr
        crop = cv2.warpAffine(bgr, M, (512, 512), borderMode=cv2.BORDER_REPLICATE)
        x = (crop[:, :, ::-1].astype(np.float32) / 255.0 - 0.5) / 0.5
        y = self.enh.run(None, {"input": x.transpose(2, 0, 1)[None]})[0][0]
        y = ((np.clip(y, -1, 1) + 1) / 2 * 255).transpose(1, 2, 0)[:, :, ::-1]
        y = crop.astype(np.float32) * (1 - strength) + y * strength
        mask = np.zeros((512, 512), np.float32)
        mask[40:472, 40:472] = 1
        mask = cv2.GaussianBlur(mask, (0, 0), 24)
        Minv = cv2.invertAffineTransform(M)
        h, w = bgr.shape[:2]
        back = cv2.warpAffine(y, Minv, (w, h), borderMode=cv2.BORDER_REPLICATE)
        m = cv2.warpAffine(mask, Minv, (w, h))[:, :, None]
        return np.clip(bgr.astype(np.float32) * (1 - m) + back * m, 0, 255).astype(np.uint8)


FACES = FaceTools()
SCAN = {}  # آخر فيديو تقلب فيه على الشخصيات


def ai_mark(bgr):
    """علامة صغيرة «AI» فالركن: الشفافية مع الناس (والقانون) ملي كيتبدل الوجه."""
    import cv2

    h, w = bgr.shape[:2]
    s = max(0.45, min(w, h) / 720)
    over = bgr.copy()
    cv2.putText(over, "AI", (int(w - 58 * s), int(h - 18 * s)), cv2.FONT_HERSHEY_SIMPLEX, 1.1 * s, (255, 255, 255),
                max(1, int(2 * s)), cv2.LINE_AA)
    return cv2.addWeighted(over, 0.55, bgr, 0.45, 0)


def normalize_video(src, dst):
    """كنوجدو الفيديو: الدوران الصحيح، مقاس معقول، وحتى 5 دقايق — باش يخدم أي فيديو ديال التليفون."""
    vf = (f"scale=w='if(gte(iw,ih),min({MAX_SIDE},iw),-2)':h='if(gte(iw,ih),-2,min({MAX_SIDE},ih))'")
    subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", src, "-t", str(MAX_SWAP_SECONDS), "-vf", vf,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", dst], check=True)


def crop_thumb(bgr, bbox, size=256):
    import cv2

    x1, y1, x2, y2 = [int(v) for v in bbox]
    cx, cy, r = (x1 + x2) // 2, (y1 + y2) // 2, int(max(x2 - x1, y2 - y1) * 0.8)
    h, w = bgr.shape[:2]
    c = bgr[max(0, cy - r):min(h, cy + r), max(0, cx - r):min(w, cx + r)]
    return cv2.resize(c, (size, size)) if c.size else np.zeros((size, size, 3), np.uint8)


def scan_characters(video_path):
    """كنقلبو على الشخصيات الرئيسية: كنجمعو الوجوه اللي كيتشابهو، ونرتبوهم حسب شحال كيبانو."""
    import cv2

    if not FACES.ready and not FACES.load():
        raise RuntimeError(FACES.status)
    work = os.path.join(OUT_DIR, "work")
    os.makedirs(work, exist_ok=True)
    norm = os.path.join(work, f"src_{uuid.uuid4().hex[:8]}.mp4")
    normalize_video(video_path, norm)
    cap = cv2.VideoCapture(norm)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    idxs = sorted(set(np.linspace(0, n - 1, min(60, n)).astype(int).tolist()))
    items = []
    for j, i in enumerate(idxs):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, fr = cap.read()
        if not ok:
            continue
        if j % 6 == 0 and FACES.nsfw_score(fr) > NSFW_LIMIT:
            cap.release()
            raise PermissionError(NSFW_MSG)
        for f in FACES.faces(fr):
            w, h = f.bbox[2] - f.bbox[0], f.bbox[3] - f.bbox[1]
            if min(w, h) < 28:
                continue
            items.append((f.normed_embedding, crop_thumb(fr, f.bbox), float(f.det_score) * w * h))
    cap.release()
    clusters = []
    for emb, thumb, q in sorted(items, key=lambda t: -t[2]):
        best = max(clusters, key=lambda c: float(np.dot(c["c"], emb)), default=None)
        if best is not None and float(np.dot(best["c"], emb)) >= CLUSTER_SIM:
            best["embs"].append(emb)
            v = np.mean(best["embs"], axis=0)
            best["c"] = v / (np.linalg.norm(v) + 1e-8)
        else:
            clusters.append({"c": emb, "embs": [emb], "thumb": thumb})
    keep = [c for c in clusters if len(c["embs"]) >= 2] or clusters
    keep = sorted(keep, key=lambda c: -len(c["embs"]))[:MAX_CHARS]
    chars = []
    for k, c in enumerate(keep):
        p = os.path.join(work, f"char_{uuid.uuid4().hex[:6]}_{k + 1}.jpg")
        cv2.imwrite(p, c["thumb"])
        chars.append({"centroid": c["c"], "thumb": p, "count": len(c["embs"])})
    SCAN.clear()
    SCAN.update(orig=video_path, video=norm, chars=chars)
    return chars


def run_swap(job, video, all_faces=False):
    """كنبدلو الوجوه لقطة بلقطة، كنوضحو الوجه، وكنرجعو الصوت الأصلي."""
    import cv2
    import imageio.v2 as imageio

    if not FACES.ready and not FACES.load():
        raise RuntimeError(FACES.status)
    job.phase = "swap"
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    job.frames_total, job.frame_i, job.t_swap = total, 0, time.time()
    cents = None if all_faces else np.stack([c["centroid"] for c in job.chars])
    tmp = os.path.join(OUT_DIR, "work", f"swap_{job.id}.mp4")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    w = imageio.get_writer(tmp, fps=fps, codec="libx264", pixelformat="yuv420p", macro_block_size=2,
                           ffmpeg_params=["-crf", "18", "-preset", "veryfast"], ffmpeg_log_level="error")
    swapped = 0
    try:
        while True:
            if job.cancel:
                raise Cancelled()
            ok, fr = cap.read()
            if not ok:
                break
            if job.frame_i % 48 == 0 and FACES.nsfw_score(fr) > NSFW_LIMIT:
                raise PermissionError(NSFW_MSG)
            found = FACES.faces(fr)
            if all_faces == "largest" and found:  # فالقصة: غير الشخصية الرئيسية (الوجه الكبير)
                found = [max(found, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))]
            for f in found:
                if all_faces:
                    src = job.sources[0]
                else:
                    sims = cents @ f.normed_embedding
                    k = int(np.argmax(sims))
                    src = job.sources[k] if sims[k] >= MATCH_SIM else None
                if src is None:
                    continue
                fr = FACES.swapper.get(fr, f, src, paste_back=True)
                if job.enhance:
                    fr = FACES.enhance(fr, f.kps)
                swapped += 1
            w.append_data(ai_mark(fr)[:, :, ::-1])
            job.frame_i += 1
    finally:
        w.close()
        cap.release()
    prefix = "swap" if not all_faces else ("story" if all_faces == "largest" else "face")
    final = os.path.join(OUT_DIR, f"{prefix}_{job.id}.mp4")
    subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", tmp, "-i", video, "-map", "0:v:0", "-map", "1:a:0?",
                    "-c:v", "copy", "-c:a", "aac", "-shortest", final], check=True)
    os.remove(tmp)
    job.out = final
    job.swapped = swapped
    if swapped == 0:
        job.note = "ℹ️ ما لقيتش وجوه نبدلهم فهاد الفيديو."


def _check_photo(img, k=None):
    f, bgr = FACES.best_face(img)
    who = f" ديال الشخصية {k}" if k else ""
    if f is None:
        return None, f"⚠️ ما لقيتش وجه واضح فالصورة{who}. جرب صورة فيها الوجه قدام وواضح."
    if FACES.nsfw_score(bgr) > NSFW_LIMIT:
        return None, NSFW_MSG
    return f, None


def scan_ui(video):
    """الزر «🔍 لقى الشخصيات»: كيرجع الصور ديال الشخصيات وكيبين الخانات ديال الصور الجديدة."""
    import gradio as gr

    touch()
    hidden = [gr.update(visible=False, value=None) for _ in range(MAX_CHARS)]
    if not video:
        return [], "⚠️ طلّع الفيديو الأول.", *hidden
    try:
        chars = scan_characters(video)
    except PermissionError as e:
        return [], str(e), *hidden
    except Exception as e:
        traceback.print_exc()
        return [], f"❌ ما قدرتش نقرا الفيديو: {e}", *hidden
    if not chars:
        return [], "ℹ️ ما لقيتش حتى وجه واضح فهاد الفيديو.", *hidden
    gal = [(c["thumb"], f"الشخصية {k + 1}") for k, c in enumerate(chars)]
    slots = [gr.update(visible=k < len(chars), value=None, label=f"📷 الوجه الجديد للشخصية {k + 1}")
             for k in range(MAX_CHARS)]
    return gal, (f"✅ لقيت **{len(chars)}** ديال الشخصيات (مرتبين من اللي كيبان بزاف). "
                 "حط الصورة الجديدة تحت رقم الشخصية اللي بغيتي تبدل، وخلي الباقي خاوي."), *slots


def submit_swap(video, enhance, consent, *photos):
    touch()
    if not consent:
        return CONSENT_MSG
    if not video or not SCAN or SCAN.get("orig") != video:
        return "⚠️ كليكي «🔍 لقى الشخصيات» الأول (من بعد ما تطلّع الفيديو)."
    sources = []
    for k, ph in enumerate(photos[:len(SCAN["chars"])]):
        if ph is None:
            sources.append(None)
            continue
        f, err = _check_photo(ph, k + 1)
        if err:
            return err
        sources.append(f)
    if not any(s is not None for s in sources):
        return "⚠️ زيد على الأقل صورة وحدة تحت شي شخصية."
    job = Job(kind="swap", phase="swap", image=None, prompts=[], n_seg=0, quality=Q_FAST, aspect=ASPECTS[0], steps=1, guidance=0,
              seed=0, translate=False, colorfix=False, video=SCAN["video"], chars=SCAN["chars"], sources=sources,
              enhance=bool(enhance))
    job.created, job.sig = time.time(), None
    JOBS.append(job)
    Q.put(job)
    n = sum(s is not None for s in sources)
    return f"✅ تزاد الطلب: تبديل {n} وجه/وجوه. غادي يبان التقدم فوق."


def submit_face_ai(face, prompt, aspect, duration, quality, steps, guidance, seed, translate, consent):
    touch()
    if not consent:
        return CONSENT_MSG
    if face is None:
        return "⚠️ زيد صورة الوجه."
    lines = [l.strip() for l in (prompt or "").splitlines() if l.strip()]
    if not lines:
        return "⚠️ كتب الموجهات: شنو بغيتي الشخص يدير وفين."
    if not FACES.ready and not FACES.load():
        return FACES.status
    f, err = _check_photo(face)
    if err:
        return err
    n_seg = max(1, int(round(float(duration) / SEG_SECONDS)))
    seed = int(seed) if seed is not None and int(seed) >= 0 else random.randint(0, 2**31 - 1)
    job = Job(kind="face_ai", image=None, prompts=lines, n_seg=n_seg, quality=quality, aspect=aspect, steps=int(steps),
              guidance=float(guidance), seed=seed, translate=bool(translate), colorfix=True, sources=[f], enhance=True)
    job.created, job.sig = time.time(), None
    JOBS.append(job)
    Q.put(job)
    return f"✅ تزاد الطلب: فيديو ديال {n_seg * 5} ثانية بالوجه ديالك. (كيتصاوب الفيديو ومن بعد كيتحط الوجه)"


# ----------------------------------------------------------------------------
# 👤 أفاتار وقصة: كتصاوب شخصية (صورة) ومن بعد فيديو قصة فيه نفس الشخصية
# ----------------------------------------------------------------------------
AV_DIR = os.path.join(OUT_DIR, "avatars")
AV_SAVED = os.path.join(AV_DIR, "saved")
AV_N = 4
AV_GENDERS = {"امرأة": "woman", "راجل": "man"}
AV_STYLES = ["أنمي", "كرتون 3D"]
STYLE_EN = {"أنمي": "anime style", "كرتون 3D": "3D animated cartoon style"}
MAX_CAST = 3
STORY_MODES = ["🎞️ كل سطر مشهد جديد", "➡️ لقطة وحدة متصلة"]
MAX_SCENES = 12
AV_PROMPT = {
    "أنمي": "High quality anime illustration of an adult {g} character{d}. Fully clothed, upper body, "
            "looking at the viewer, clean simple background",
    "كرتون 3D": "3D animated film character render of an adult {g}{d}. Fully clothed, upper body, "
                "looking at the camera, soft lighting, clean simple background",
}
BG_PROMPT = ("{st} illustration of the setting: {s}. Background only, empty scene with no people, wide shot, "
             "detailed, high quality")
MOTION_PROMPT = ("{st} animation. {who}: {s}. Family friendly, fully clothed, expressive faces, smooth natural motion, "
                 "high quality")
WHO = {1: "One character", 2: "Two characters side by side", 3: "Three characters side by side"}
# حماية: بلا محتوى جنسي، والشخصية ديما كبيرة (+18)
_SEXUAL = re.compile(r"(nud(e|ity)|naked|nsfw|porn|\bsex|erotic|lingerie|topless|nipple|boob|breast|underwear|"
                     r"\bnue?s?\b|\bseins?\b|érotique|erotique|sous-v[eê]tement|"
                     r"عاري|عارية|عريان|عريانة|عراة|بلا حوايج|بلا ملابس|جنس|سكس|بورن|إباح|اباح|ملابس داخلية)", re.I)
_MINOR = re.compile(r"(\bchild|\bkid|\bteen|\bminor\b|underage|schoolgirl|schoolboy|\bloli|\bbaby|\benfant|"
                    r"\bado\b|adolescent|gamin|fillette|طفل|أطفال|اطفال|مراهق|بنت صغيرة|ولد صغير|\bدرية\b|تلميذ)", re.I)
_AGE = re.compile(r"(\d{1,2})\s*(ans\b|an\b|years?\b|yrs?\b|yo\b|y/o|عام|سنة|سنين)", re.I)
SEX_MSG = "⛔ التطبيق ما كيصاوبش محتوى عريان ولا جنسي. بدّل الوصف وعاود."
MINOR_MSG = "⛔ الشخصية خاصها تكون كبيرة (+18). بدّل الوصف وعاود."
AVATAR_META = {}  # الصورة ← المعلومات ديالها (الجنس، الأسلوب، الوصف)


def check_text(text, avatar=False):
    """كيرجع رسالة إلا كان الوصف ممنوع، وإلا None."""
    for t in {text or "", to_english(text) if text else ""}:
        if _SEXUAL.search(t):
            return SEX_MSG
        if avatar and (_MINOR.search(t) or any(int(m.group(1)) < 18 for m in _AGE.finditer(t))):
            return MINOR_MSG
    return None


def _save_card(img, meta, path):
    """كنحفظو الصورة مع المعلومات داخلها، باش ترجع الشخصية كاملة إلا رفعتيها مرة أخرى."""
    from PIL.PngImagePlugin import PngInfo

    info = PngInfo()
    info.add_itxt("wasset_avatar", json.dumps({k: v for k, v in meta.items() if k != "path"}, ensure_ascii=False))
    img.save(path, pnginfo=info)


def _read_card(path):
    try:
        raw = Image.open(path).info.get("wasset_avatar")
        meta = json.loads(raw) if raw else None
        return meta if isinstance(meta, dict) and meta.get("style") in AV_STYLES else None
    except Exception:
        return None


def _av_info(meta):
    if not meta:
        return ""
    name = meta.get("name") or "بلا سمية"
    kind = meta.get("toon") or meta.get("style", "")
    desc = f" — {meta['desc']}" if meta.get("desc") else ""
    tip = "" if meta.get("name") else "  \nعطيها سمية و«💾 زيدها للشخصيات» باش تمتل فالقصة."
    return f"**الشخصية:** {name} · {meta.get('gender', '')} · {kind}{desc}{tip}"


def latest_avatar_cands():
    for j in reversed(JOBS):
        if getattr(j, "kind", "") == "avatar" and getattr(j, "cands", None):
            return [p for p in j.cands if os.path.exists(p)]
    return []


def saved_avatars():
    if not os.path.isdir(AV_SAVED):
        return []
    ps = sorted((os.path.join(AV_SAVED, f) for f in os.listdir(AV_SAVED) if f.endswith(".png")),
                key=os.path.getmtime, reverse=True)
    return [(p, (_read_card(p) or {}).get("name") or "") for p in ps]


def cast_names():
    return [n for _, n in saved_avatars() if n]


def cast_card(name):
    for p, n in saved_avatars():
        if n == name:
            return p
    return None


def run_avatar(job):
    """كنصاوبو 4 ديال الصور (لقطة وحدة من الموديل لكل صورة) وكنحيدو أي صورة فيها +18."""
    os.makedirs(AV_DIR, exist_ok=True)
    if not FACES.ready:
        FACES.load()
    w, h = QUALITY[job.quality]["sizes"]["عمودي 9:16"]
    job.cands, flagged, spent = [], 0, 0.0

    def on_step(s, _t=[time.time()]):
        nonlocal spent
        if job.cancel:
            raise Cancelled()
        now = time.time()
        if s > 1:
            spent += now - _t[0]
            job.done_steps += 1
            job.sec_per_step = spent / job.done_steps
        _t[0] = now
        job.step = s

    for k in range(AV_N):
        if job.cancel:
            raise Cancelled()
        job.seg_i, job.step = k + 1, 0
        job.msg = f"كنصاوب الصورة {k + 1} من {AV_N}"
        args = (job.prompts[0], None, w, h, job.steps, job.guidance, job.seed + k, on_step)
        try:
            frames = ENGINE.segment(*args, num_frames=1)
        except RuntimeError as e:
            if "NAN_RESULT" not in str(e) or not ENGINE.to_bf16():
                raise
            frames = ENGINE.segment(*args, num_frames=1)
        if FACES.ready and FACES.nsfw_score(np.ascontiguousarray(frames[0][:, :, ::-1])) > NSFW_LIMIT:
            flagged += 1
            continue
        p = os.path.join(AV_DIR, f"cand_{job.id}_{k + 1}.png")
        meta = dict(job.meta, seed=job.seed + k)
        _save_card(Image.fromarray(frames[0]), meta, p)
        AVATAR_META[p] = meta
        job.cands.append(p)
    if not job.cands:
        raise PermissionError(SEX_MSG)
    job.state = "done"
    job.msg = f"✅ {len(job.cands)} ديال الصور ديال الشخصية واجدين — كليكي على اللي عجباتك."
    if flagged:
        job.msg += f" (تحيدو {flagged} ما مناسبينش)"


def submit_avatar(gender, style, desc, quality, steps, guidance, seed, translate):
    touch()
    err = check_text(desc, avatar=True)
    if err:
        return err
    d_en = (to_english(desc) if translate else desc or "").strip().rstrip(".")
    prompt = AV_PROMPT[style].format(g=AV_GENDERS.get(gender, "person"), d=f", {d_en}" if d_en else "")
    seed = int(seed) if seed is not None and int(seed) >= 0 else random.randint(0, 2**31 - 1)
    meta = {"gender": gender, "style": style, "desc": (desc or "").strip(), "desc_en": d_en, "source": "gen", "name": ""}
    job = Job(kind="avatar", image=None, prompts=[prompt], n_seg=AV_N, quality=quality, aspect=ASPECTS[0],
              steps=int(steps), guidance=float(guidance), seed=seed, translate=False, colorfix=False, meta=meta)
    job.created, job.sig = time.time(), None
    JOBS.append(job)
    Q.put(job)
    ahead = sum(1 for j in JOBS if j.state in ("queued", "running")) - 1
    wait = f" (قبلو {ahead} طلب فاللائحة)" if ahead > 0 else ""
    return f"✅ تزاد الطلب: {AV_N} ديال الصور ديال الشخصية{wait}. غادي يبانو تحت «اختار الصورة»."


def _gal_path(value, evt):
    """كنجبدو الطريق ديال الصورة اللي تكليكات فالمعرض (كيخدم مع جميع الأشكال ديال Gradio)."""
    v = getattr(evt, "value", None)
    if isinstance(v, dict):
        img = v.get("image") or v
        if isinstance(img, dict) and img.get("path"):
            return img["path"]
    try:
        item = (value or [])[evt.index]
    except Exception:
        return None
    if isinstance(item, (list, tuple)):
        item = item[0]
    if isinstance(item, dict):
        item = (item.get("image") or {}).get("path") or item.get("path")
    return item if isinstance(item, str) else None


def _pick(path, saved=False):
    meta = dict(AVATAR_META.get(path) or _read_card(path) or {})
    if not path or not meta:
        return None, None, "⚠️ ما قدرتش نقرا هاد الصورة. عاود اختار."
    meta["path"] = path
    return meta, path, _av_info(meta)


def save_avatar(av, name):
    if not av:
        return "⚠️ اختار شخصية الأولى.", None, saved_avatars(), av
    name = re.sub(r"\s+", " ", (name or "").strip())[:30]
    if not name:
        return "⚠️ عطي سمية للشخصية (مثلاً: منير، ياسين).", None, saved_avatars(), av
    os.makedirs(AV_SAVED, exist_ok=True)
    old = cast_card(name)
    if old:
        os.remove(old)
    safe = re.sub(r"[^\w\-]+", "_", name)
    dst = os.path.join(AV_SAVED, f"{safe}_{uuid.uuid4().hex[:4]}.png")
    meta = dict(av, name=name)
    _save_card(Image.open(av["path"]).convert("RGB"), meta, dst)
    meta["path"] = dst
    AVATAR_META[dst] = meta
    return (f"💾 «{name}» تزادت للشخصيات. حمّل البطاقة وخليها فالتيليفون: إلا رفعتيها مرة أخرى كترجع كاملة."), \
        dst, saved_avatars(), meta


def upload_avatar(file):
    """رفع بطاقة شخصية محفوظة (الملف اللي حمّلتي من «💾»)، كترجع للشخصيات."""
    path = file if isinstance(file, str) else getattr(file, "name", None)
    if not path:
        return "", saved_avatars()
    meta = _read_card(path)
    if not meta or not meta.get("name"):
        return "⚠️ هادي ماشي بطاقة شخصية. باش تصاوب شخصية من صورة استعمل «🎨 رجعها كرتونية».", saved_avatars()
    img = Image.open(path).convert("RGB")
    if FACES.ready and FACES.nsfw_score(np.ascontiguousarray(np.asarray(img)[:, :, ::-1])) > NSFW_LIMIT:
        return NSFW_MSG, saved_avatars()
    os.makedirs(AV_SAVED, exist_ok=True)
    old = cast_card(meta["name"])
    if old:
        os.remove(old)
    dst = os.path.join(AV_SAVED, f"{re.sub(r'[^\w\-]+', '_', meta['name'])}_{uuid.uuid4().hex[:4]}.png")
    _save_card(img, meta, dst)
    AVATAR_META[dst] = dict(meta, path=dst)
    return f"✅ رجعات «{meta['name']}» للشخصيات.", saved_avatars()


def story_start(job, i, w, h):
    """البداية ديال كل مشهد: خلفية جديدة من الوصف + الشخصيات الكرتونية فوقها."""
    job.msg = f"🖼️ كنحضّر المشهد {i + 1} من {job.n_seg}"

    def check(s):
        if job.cancel:
            raise Cancelled()

    args = (job.bg_prompts[i], None, w, h, max(8, int(job.steps * 0.7)), job.guidance, job.seed + 1000 + i, check)
    try:
        frames = ENGINE.segment(*args, num_frames=1)
    except RuntimeError as e:
        if "NAN_RESULT" not in str(e) or not ENGINE.to_bf16():
            raise
        frames = ENGINE.segment(*args, num_frames=1)
    bg = Image.fromarray(frames[0])
    try:
        cuts = [TOON.cutout(p) for p in job.scene_cast[i]]
    except Exception as e:  # إلا ما خدمش القطع: كنبداو من صورة الشخصية الأولى
        log("cutout failed:", e)
        job.note = "ℹ️ ما قدرتش نقطع الخلفية ديال الشخصيات، بديت من الصورة ديالهم."
        return fit_image(Image.open(job.scene_cast[i][0]).convert("RGB"), w, h)
    return compose_scene(bg, cuts, w, h)


def submit_story(cast, story, mode, aspect, quality, steps, guidance, seed, translate):
    touch()
    cast = [c for c in (cast or []) if cast_card(c)]
    if not cast:
        return "⚠️ اختار شخصية وحدة على الأقل من «🎭 الشخصيات اللي غادي يمتلو»."
    if len(cast) > MAX_CAST:
        return f"⚠️ حتى {MAX_CAST} ديال الشخصيات فالقصة."
    lines = [l.strip() for l in (story or "").splitlines() if l.strip()]
    if not lines:
        return "⚠️ كتب القصة: كل سطر = مشهد ديال 5 ثواني."
    note = ""
    if len(lines) > MAX_SCENES:
        lines, note = lines[:MAX_SCENES], f" (خديت غير أول {MAX_SCENES} سطر)"
    err = check_text("\n".join(lines))
    if err:
        return err
    if not FACES.ready and not FACES.load():
        return FACES.status
    cards = {c: cast_card(c) for c in cast}
    style = STYLE_EN.get((_read_card(cards[cast[0]]) or {}).get("style"), "anime style")
    bg, motion, who = [], [], []
    for line in lines:
        here = [c for c in cast if c in line] or cast   # إلا ذكرتي سمية فالسطر، غير هي اللي كتبان
        s_en = (to_english(line) if translate else line).strip().rstrip(".")
        bg.append(BG_PROMPT.format(st=style[0].upper() + style[1:], s=s_en))
        motion.append(MOTION_PROMPT.format(st=style[0].upper() + style[1:], who=WHO[len(here)], s=s_en))
        who.append([cards[c] for c in here])
    seed = int(seed) if seed is not None and int(seed) >= 0 else random.randint(0, 2**31 - 1)
    job = Job(kind="story", image=None, chain=mode == STORY_MODES[1], prompts=motion, bg_prompts=bg, scene_cast=who,
              n_seg=len(lines), quality=quality, aspect=aspect, steps=int(steps), guidance=float(guidance), seed=seed,
              translate=False, colorfix=True, sources=[], enhance=False)
    job.created, job.sig = time.time(), None
    JOBS.append(job)
    Q.put(job)
    return (f"✅ تزاد الطلب: قصة ديال {len(lines)} مشاهد ({len(lines) * 5} ثانية) بـ {'، '.join(cast)}{note}. "
            "كل مشهد: كنرسم المكان، كنحط الشخصيات، ومن بعد كيتحركو.")


# ----------------------------------------------------------------------------
# 🎨 من صورة إلى كرتون (AnimeGANv2 — الشبكة مكتوبة هنا، رخصة MIT © 2021 Bryan Lee،
#    github.com/bryandlee/animegan2-pytorch) + قطع الخلفية (U²-Net human seg، Apache-2.0)
# ----------------------------------------------------------------------------
TOON_ROOT = os.path.join(FACE_ROOT, "toon")
_AG = "https://raw.githubusercontent.com/bryandlee/animegan2-pytorch/main/weights/"
TOON_STYLES = {  # الاسم اللي كيبان ← الملف
    "أنمي ناعم": "face_paint_512_v2",
    "أنمي قوي": "face_paint_512_v1",
    "رسم ملون": "celeba_distill",
    "ألوان زاهية": "paprika",
}
TOON_FILES = {f"{v}.pt": _AG + f"{v}.pt" for v in TOON_STYLES.values()}
TOON_FILES["u2net_human_seg.onnx"] = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx"


def _toon_net():
    import torch
    from torch import nn
    import torch.nn.functional as F

    class ConvNormLReLU(nn.Sequential):
        def __init__(self, i, o, k=3, s=1, p=1, groups=1, bias=False):
            super().__init__(nn.ReflectionPad2d(p), nn.Conv2d(i, o, k, s, 0, groups=groups, bias=bias),
                             nn.GroupNorm(1, o, affine=True), nn.LeakyReLU(0.2, inplace=True))

    class InvRes(nn.Module):
        def __init__(self, i, o, r=2):
            super().__init__()
            self.use_res_connect = i == o
            b = int(round(i * r))
            self.layers = nn.Sequential(ConvNormLReLU(i, b, k=1, p=0), ConvNormLReLU(b, b, groups=b, bias=True),
                                        nn.Conv2d(b, o, 1, 1, 0, bias=False), nn.GroupNorm(1, o, affine=True))

        def forward(self, x):
            y = self.layers(x)
            return x + y if self.use_res_connect else y

    class Generator(nn.Module):
        def __init__(self):
            super().__init__()
            self.block_a = nn.Sequential(ConvNormLReLU(3, 32, k=7, p=3), ConvNormLReLU(32, 64, s=2, p=(0, 1, 0, 1)),
                                         ConvNormLReLU(64, 64))
            self.block_b = nn.Sequential(ConvNormLReLU(64, 128, s=2, p=(0, 1, 0, 1)), ConvNormLReLU(128, 128))
            self.block_c = nn.Sequential(ConvNormLReLU(128, 128), InvRes(128, 256), InvRes(256, 256), InvRes(256, 256),
                                         InvRes(256, 256), ConvNormLReLU(256, 128))
            self.block_d = nn.Sequential(ConvNormLReLU(128, 128), ConvNormLReLU(128, 128))
            self.block_e = nn.Sequential(ConvNormLReLU(128, 64), ConvNormLReLU(64, 64), ConvNormLReLU(64, 32, k=7, p=3))
            self.out_layer = nn.Sequential(nn.Conv2d(32, 3, 1, 1, 0, bias=False), nn.Tanh())

        def forward(self, x):
            y = self.block_a(x)
            half = y.size()[-2:]
            y = self.block_c(self.block_b(y))
            y = self.block_d(F.interpolate(y, half, mode="bilinear", align_corners=True))
            y = self.block_e(F.interpolate(y, x.size()[-2:], mode="bilinear", align_corners=True))
            return self.out_layer(y)

    return torch, Generator


class Toon:
    """كيرجع الصورة كرتونية (4 ستيلات) وكيقطع الشخصية من الخلفية."""

    def __init__(self):
        self.nets, self.seg, self._lock, self.error = {}, None, threading.Lock(), None
        self._cut = {}

    def _get(self, name):
        os.makedirs(TOON_ROOT, exist_ok=True)
        p = os.path.join(TOON_ROOT, name)
        if not os.path.exists(p):
            import requests

            log("downloading", name)
            r = requests.get(TOON_FILES[name], timeout=600)
            r.raise_for_status()
            open(p + ".part", "wb").write(r.content)
            os.replace(p + ".part", p)
        return p

    def net(self, style):
        f = TOON_STYLES[style]
        with self._lock:
            if f not in self.nets:
                torch, Generator = _toon_net()
                g = Generator()
                g.load_state_dict(torch.load(self._get(f + ".pt"), map_location="cpu", weights_only=True))
                self.nets[f] = g.eval()
            return self.nets[f]

    def cartoon(self, img, style):
        import torch

        g = self.net(style)
        x = torch.from_numpy(np.asarray(img, np.float32) / 127.5 - 1).permute(2, 0, 1)[None]
        with torch.no_grad():
            y = g(x)[0].clamp(-1, 1)
        return Image.fromarray(((y.permute(1, 2, 0).numpy() + 1) * 127.5).round().astype(np.uint8))

    def mask(self, img):
        """قناع الشخصية (أبيض = الشخصية)."""
        import onnxruntime as ort

        with self._lock:
            if self.seg is None:
                self.seg = ort.InferenceSession(self._get("u2net_human_seg.onnx"), providers=["CPUExecutionProvider"])
        a = np.asarray(img.convert("RGB").resize((320, 320), Image.BILINEAR), np.float32) / 255.0
        a = (a - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
        m = self.seg.run(None, {self.seg.get_inputs()[0].name: a.transpose(2, 0, 1)[None].astype(np.float32)})[0][0, 0]
        m = (m - m.min()) / max(1e-6, float(m.max() - m.min()))
        return Image.fromarray((m * 255).astype(np.uint8)).resize(img.size, Image.BILINEAR)

    def cutout(self, path):
        """الشخصية بلا خلفية (RGBA)، محفوظة فالذاكرة."""
        from PIL import ImageFilter

        if path not in self._cut:
            img = Image.open(path).convert("RGB")
            m = self.mask(img).filter(ImageFilter.GaussianBlur(1.5))
            rgba = img.convert("RGBA")
            rgba.putalpha(m)
            box = m.point(lambda v: 255 if v > 40 else 0).getbbox()
            self._cut[path] = rgba.crop(box) if box else rgba
        return self._cut[path]


TOON = Toon()


def portrait_crop(img):
    """كنقصو الصورة حول الوجه (الرأس والكتفين)، بالطول 3:4، وكنخليو المقاسات مضروبة فـ 32."""
    f = None
    if FACES.ready:
        f, _ = FACES.best_face(img)
    W, H = img.size
    if f is not None:
        x1, y1, x2, y2 = [float(v) for v in f.bbox]
        fw, cx = x2 - x1, (x1 + x2) / 2
        cw = min(W, fw * 2.8)
        ch = min(H, cw * 4 / 3)
        cw = ch * 3 / 4
        left = min(max(0, cx - cw / 2), W - cw)
        top = min(max(0, y1 - fw * 0.75), H - ch)
        img = img.crop((int(left), int(top), int(left + cw), int(top + ch)))
    else:
        ch = min(H, W * 4 / 3)
        cw = ch * 3 / 4
        img = img.crop((int((W - cw) / 2), int((H - ch) / 2), int((W + cw) / 2), int((H + ch) / 2)))
    return img.resize((512, 672), Image.LANCZOS)


def compose_scene(bg, cutouts, w, h):
    """كنحطو الشخصيات (بلا خلفية) فالمشهد، الواحد حدا الآخر، لتحت."""
    scene = bg.convert("RGB").resize((w, h), Image.LANCZOS)
    n = len(cutouts)
    if not n:
        return scene
    th = h * (0.8 if n == 1 else 0.66 if n == 2 else 0.56)
    parts = [c.resize((max(1, int(c.width * th / c.height)), int(th)), Image.LANCZOS) for c in cutouts]
    total = sum(p.width for p in parts)
    if total > w * 0.96:
        k = w * 0.96 / total
        parts = [p.resize((max(1, int(p.width * k)), max(1, int(p.height * k))), Image.LANCZOS) for p in parts]
    for i, p in enumerate(parts):
        cx = w * (i + 1) / (n + 1)
        scene.paste(p, (int(cx - p.width / 2), h - p.height), p)
    return scene


def cartoonize_ui(photo, gender, consent):
    """الزر «🎨 رجعها كرتونية»: 4 ستيلات من نفس الصورة."""
    touch()
    if photo is None:
        return [], "⚠️ زيد صورة فيها الوجه واضح."
    if not consent:
        return [], CONSENT_MSG
    if not FACES.ready and not FACES.load():
        return [], FACES.status
    img = ImageOps.exif_transpose(photo).convert("RGB")
    f, err = _check_photo(img)
    if err:
        return [], err
    base = portrait_crop(img)
    os.makedirs(AV_DIR, exist_ok=True)
    tag, out = uuid.uuid4().hex[:6], []
    try:
        for name in TOON_STYLES:
            toon = TOON.cartoon(base, name)
            p = os.path.join(AV_DIR, f"toon_{tag}_{TOON_STYLES[name]}.png")
            meta = {"gender": gender, "style": "أنمي", "toon": name, "desc": "", "desc_en": "", "source": "photo",
                    "name": ""}
            _save_card(toon, meta, p)
            AVATAR_META[p] = meta
            out.append((p, name))
    except Exception as e:
        traceback.print_exc()
        return [], f"❌ ما قدرتش نرجعها كرتونية: {e}"
    return out, "✅ هاهوما 4 ديال الستيلات — كليكي على اللي عجبك، ومن بعد عطيه سمية و«💾 زيدها للشخصيات»."


# ----------------------------------------------------------------------------
# الواجهة (نفس الروح ديال Yollo، بلا جواهر بلا اشتراك)
# ----------------------------------------------------------------------------
def submit(image, prompt, duration, quality, aspect, steps, guidance, seed, translate, colorfix, _dedupe=True):
    touch()
    lines = [l.strip() for l in (prompt or "").splitlines() if l.strip()]
    sig = (getattr(image, "size", None), tuple(lines), duration, quality, aspect)
    for j in JOBS[-5:]:
        if (_dedupe and j.state in ("queued", "running") and getattr(j, "sig", None) == sig and seed in (None, -1)
                and time.time() - j.created < 20):
            return "⏳ هاد الطلب ديجا فاللائحة (ما تضغطش جوج مرات)."
    if not lines:
        if image is None:
            return "⚠️ كتب الموجهات (صف الفيديو) ولا زيد صورة."
        lines = [DEFAULT_PROMPT]
    n_seg = max(1, int(round(float(duration) / SEG_SECONDS)))
    seed = int(seed) if seed is not None and int(seed) >= 0 else random.randint(0, 2**31 - 1)
    job = Job(image=image, prompts=lines, n_seg=n_seg, quality=quality, aspect=aspect, steps=int(steps),
              guidance=float(guidance), seed=seed, translate=bool(translate), colorfix=bool(colorfix))
    job.sig, job.created = sig, time.time()
    JOBS.append(job)
    LAST.clear()
    LAST.update(image=image, prompt=prompt, duration=duration, quality=quality, aspect=aspect, steps=steps,
                guidance=guidance, translate=translate, colorfix=colorfix)
    Q.put(job)
    ahead = sum(1 for j in JOBS if j.state in ("queued", "running")) - 1
    return f"✅ تزاد الطلب: {n_seg * 5} ثانية. " + (f"قدامك {ahead} فاللائحة." if ahead else "بدا دابا.")


def again():
    """نفس الصورة، نفس الوصف، نفس المدة والجودة… غير البذرة كتبدل باش تخرج نسخة مختلفة."""
    touch()
    if not LAST:
        return "⚠️ مازال ما صاوبتي حتى فيديو. صاوب واحد الأول ومن بعد عاود."
    return "🔁 نسخة أخرى بنفس الإعدادات — " + submit(**LAST, seed=-1, _dedupe=False)


def cancel_all():
    touch()
    n = 0
    for j in JOBS:
        if j.state in ("queued", "running"):
            j.cancel = True
            n += 1
    return f"⏹️ غادي يتوقف ({n})" if n else "ما كاين حتى طلب خدام."


def status_md():
    st = ENGINE.status
    if not ENGINE.ready and ENGINE.error is None and getattr(ENGINE, "t_load", None):
        st += f" (دازت {int((time.time() - ENGINE.t_load) // 60)} دقيقة)"
    lines = [f"**المحرك:** {st}"]
    if FACES.ready or FACES.error or FACES._lock.locked():
        lines.append(f"**أدوات الوجوه:** {FACES.status}")
    active = [j for j in JOBS if j.state in ("queued", "running")]
    for j in active:
        if j.state == "running" and getattr(j, "phase", "gen") == "swap":
            if not j.frames_total:
                lines.append(f"🎭 **{j.msg}**")
            else:
                pct = int(100 * j.frame_i / max(1, j.frames_total))
                lines.append(f"🎭 **{j.msg}** — اللقطة {j.frame_i}/{j.frames_total} — **{pct}%** — "
                             f"باقي تقريباً: **{fmt_min(eta(j))}**")
        elif j.state == "running":
            pct = max(0, min(100, int(100 * ((j.seg_i - 1) * j.steps + j.step) / max(1, j.n_seg * j.steps))))
            lines.append(f"🎬 **{j.msg}** — **{pct}%** — باقي تقريباً: **{fmt_min(eta(j))}**")
        else:
            k = getattr(j, "kind", "gen")
            what = {"swap": "تبديل الوجوه", "avatar": f"{AV_N} صور ديال الشخصية",
                    "story": f"قصة ديال {j.n_seg * 5} ثانية"}.get(k, f"{j.n_seg * 5} ثانية")
            lines.append(f"⏳ طلب فاللائحة ({what}) — {j.msg}")
    last = [j for j in JOBS if j.state in ("done", "error", "cancelled")][-1:]
    for j in last:
        lines.append(f"**آخر طلب:** {j.msg}")
    return "  \n".join(lines)


def list_videos():
    if not os.path.isdir(OUT_DIR):
        return []
    files = [os.path.join(OUT_DIR, f) for f in os.listdir(OUT_DIR) if f.endswith(".mp4")]
    return sorted(files, key=os.path.getmtime, reverse=True)


def latest_video():
    for j in reversed(JOBS):
        if j.out and os.path.exists(j.out):
            return j.out
    v = list_videos()
    return v[0] if v else None


CSS = """
.gradio-container {direction: rtl; max-width: 680px !important; margin: auto;}
.gradio-container input, .gradio-container textarea {text-align: right;}
#hdr h1 {font-size: 1.45em; margin: 0;}
.gen-btn {background: linear-gradient(90deg, #7c3aed, #c026d3, #db2777) !important; color: #fff !important;
          font-size: 1.2em !important; min-height: 56px; border-radius: 16px !important; border: none !important;}
.tabs button[role=tab] {font-size: 1.02em;}
.tabs button[role=tab][aria-selected=true] {background: linear-gradient(90deg, #4f46e5, #9333ea); color: #fff !important;
          border-radius: 12px;}
#status {border-radius: 12px; padding: 6px 10px; background: rgba(147, 51, 234, .12);}
html, body, .gradio-container {overflow-x: hidden !important;}
#mode .wrap {display: grid !important; grid-template-columns: 1fr 1fr; gap: 8px;}
#mode label {justify-content: center; padding: 10px 6px; border-radius: 14px; font-weight: 600;}
#mode label.selected, #mode label:has(input:checked) {background: linear-gradient(90deg, #4f46e5, #9333ea) !important;
          color: #fff !important;}
#mode input[type=radio] {display: none;}
#mode label:last-child {grid-column: 1 / -1;}
footer {display: none !important;}
"""
# كيعلم تطبيق التيليفون («فيديو AI») بلي الصفحة تحلات داخلو
HEAD = ("<script>try{document.body&&document.body.classList.add('dark');"
        "document.addEventListener('DOMContentLoaded',()=>document.body.classList.add('dark'));"
        "if(window.parent!==window)window.parent.postMessage({wasset:'ready'},'*')}catch(e){}</script>")


def make_theme():
    import gradio as gr

    return gr.themes.Soft(primary_hue="purple", secondary_hue="pink", radius_size="lg").set(
        body_background_fill_dark="#0e0e14",
        block_background_fill_dark="#1a1a24",
        input_background_fill_dark="#2a2a36",
        block_label_background_fill_dark="#2a2a36",
        button_primary_background_fill_dark="linear-gradient(90deg, #7c3aed, #db2777)",
        button_primary_background_fill_hover_dark="linear-gradient(90deg, #6d28d9, #be185d)",
    )


MODES = ["🖼️ صورة إلى فيديو", "✍️ نص إلى فيديو", "🎭 تبديل الوجوه", "🌟 وجهي فـ فيديو AI", "👤 أفاتار كرتون وقصة"]


def build_ui():
    import gradio as gr

    with gr.Blocks(title="فيديو بالذكاء الاصطناعي") as demo:
        gr.Markdown("# ✨ فيديو بالذكاء الاصطناعي\nإنشائي · فابور · بلا حدود", rtl=True, elem_id="hdr")
        status = gr.Markdown(status_md(), rtl=True, elem_id="status")
        info = gr.Markdown(rtl=True)

        mode = gr.Radio(MODES, value=MODES[0], show_label=False, elem_id="mode")
        with gr.Column(visible=True) as g_img:
                gr.Markdown("**صورة إلى فيديو:** الصورة كتولي فيديو كيتحرك.", rtl=True)
                image = gr.Image(label="الصورة", type="pil", sources=["upload"], height=260)
                prompt_i = gr.Textbox(label="الموجهات *", placeholder="صف الحركة اللي بغيتي فالفيديو…\n"
                                      "(كل سطر = 5 ثواني)", lines=4, max_length=5000, rtl=True)
                go_i = gr.Button("✨ إنشاء", elem_classes="gen-btn")
        with gr.Column(visible=False) as g_txt:
                gr.Markdown("**نص إلى فيديو:** كتب شنو بغيتي والفيديو كيتصاوب من الصفر.", rtl=True)
                prompt_t = gr.Textbox(label="الموجهات *", placeholder="صف الفيديو الذي تريد إنشاءه…\n"
                                      "(كل سطر = 5 ثواني)", lines=5, max_length=5000, rtl=True)
                aspect = gr.Radio(ASPECTS, value=ASPECTS[0], label="📐 الشكل")
                go_t = gr.Button("✨ إنشاء", elem_classes="gen-btn")
        with gr.Column(visible=False) as g_swap:
                gr.Markdown("**تبديل الوجوه فالفيديو:** 1️⃣ طلّع الفيديو (حتى 5 دقايق) ← 2️⃣ «لقى الشخصيات» ← "
                            "3️⃣ حط الوجه الجديد تحت رقم كل شخصية بغيتي تبدلها ← 4️⃣ «بدّل الوجوه».", rtl=True)
                sw_video = gr.Video(label="📹 الفيديو", sources=["upload"], height=260, elem_id="sw_video")
                scan_btn = gr.Button("🔍 لقى الشخصيات")
                chars_gal = gr.Gallery(label="الشخصيات اللي فالفيديو", columns=3, height=230, object_fit="cover")
                chars_info = gr.Markdown(rtl=True)
                with gr.Row():
                    slots = [gr.Image(label=f"📷 الوجه الجديد للشخصية {k + 1}", type="pil", sources=["upload"],
                                      visible=False, height=170, min_width=120, elem_id=f"slot{k}") for k in range(MAX_CHARS)]
                sw_enh = gr.Checkbox(value=True, label="✨ وضّح الوجه (جودة أحسن، أبطأ شوية)")
                sw_ok = gr.Checkbox(value=False, label="✅ كنأكد بلي عندي الإذن ديال الناس اللي فالفيديو والصور، "
                                                       "والاستعمال شخصي")
                go_sw = gr.Button("🎭 بدّل الوجوه", elem_classes="gen-btn")
        with gr.Column(visible=False) as g_face:
                gr.Markdown("**وجهي فـ فيديو AI:** عطيه صورة وجهك ووصف، وكيصاوب فيديو جديد فيه نتا.", rtl=True)
                fa_face = gr.Image(label="📷 صورة الوجه (قدام وواضح)", type="pil", sources=["upload"], height=220)
                fa_prompt = gr.Textbox(label="الموجهات *", placeholder="مثال: راجل لابس كوستيم كيتمشى فشاطئ وقت الغروب، "
                                       "والكاميرا كتبعو\n(كل سطر = 5 ثواني)", lines=4, max_length=5000, rtl=True)
                fa_aspect = gr.Radio(ASPECTS, value=ASPECTS[0], label="📐 الشكل")
                fa_ok = gr.Checkbox(value=False, label="✅ هادا وجهي، ولا عندي الإذن ديال مولاه")
                go_fa = gr.Button("🌟 إنشاء", elem_classes="gen-btn")
        with gr.Column(visible=False) as g_story:
                gr.Markdown("**👤 أفاتار كرتون وقصة:** 1️⃣ صورة ← كرتون ← 2️⃣ عطيها سمية وزيدها للشخصيات "
                            "(عاود لكل شخص) ← 3️⃣ اختار الشخصيات وكتب القصة ← 4️⃣ «صاوب القصة».", rtl=True)
                with gr.Accordion("1️⃣ الشخصيات", open=True):
                    av_src = gr.Radio(["📷 من صورة", "✍️ من وصف"], value="📷 من صورة", show_label=False)
                    av_gender = gr.Radio(list(AV_GENDERS), value="راجل", label="👤 الجنس")
                    with gr.Column(visible=True) as g_av_photo:
                        av_photo = gr.Image(label="📷 الصورة (الوجه قدام وواضح)", type="pil", sources=["upload"],
                                            height=220, elem_id="av_photo")
                        av_ok = gr.Checkbox(value=False, label="✅ هادي صورتي، ولا عندي الإذن ديال مولاها",
                                            elem_id="av_ok")
                        toon_btn = gr.Button("🎨 رجعها كرتونية", elem_id="toon_btn")
                    with gr.Column(visible=False) as g_av_desc:
                        av_style = gr.Radio(AV_STYLES, value=AV_STYLES[0], label="🎨 الأسلوب")
                        av_desc = gr.Textbox(label="الوصف", lines=2, max_length=500, rtl=True, elem_id="av_desc",
                                             placeholder="مثال: 30 عام، شعر كحل، جلابة بيضاء، ابتسامة")
                        av_go = gr.Button("✨ صاوب 4 ديال الصور", elem_id="av_go")
                    av_gal = gr.Gallery(label="اختار الستيل (كليكي على الصورة)", columns=2, height=400,
                                        object_fit="cover", allow_preview=False, value=latest_avatar_cands(),
                                        elem_id="av_gal")
                    av_cur = gr.Image(label="✅ المختارة", interactive=False, height=220, elem_id="av_cur")
                    av_info = gr.Markdown(rtl=True, elem_id="av_info")
                    with gr.Row():
                        av_name = gr.Textbox(label="السمية", placeholder="مثلاً: منير", max_length=30, rtl=True,
                                             scale=3, elem_id="av_name")
                        av_save = gr.Button("💾 زيدها للشخصيات", scale=2, min_width=120, elem_id="av_save")
                    av_card = gr.File(label="⬇️ بطاقة الشخصية (حفظها فالتيليفون باش ترجعها من بعد)",
                                      interactive=False)
                    av_saved = gr.Gallery(label="🗂️ الشخصيات ديالك", columns=4, height=160, object_fit="cover",
                                          allow_preview=False, value=saved_avatars(), elem_id="av_saved")
                    av_up = gr.File(label="📂 رجّع شخصية محفوظة (البطاقة)", file_types=["image"], elem_id="av_up")
                with gr.Accordion("2️⃣ القصة", open=True):
                    st_cast = gr.CheckboxGroup(cast_names(), label=f"🎭 الشخصيات اللي غادي يمتلو (حتى {MAX_CAST})",
                                               elem_id="st_cast")
                    st_story = gr.Textbox(label="القصة * (كل سطر = مشهد 5 ثواني، حتى 12)", lines=6,
                                          max_length=3000, rtl=True, elem_id="st_story",
                                          placeholder="منير وياسين كيتمشاو فسوق مكناس القديم\n"
                                                      "كيشربو أتاي فالسطح وقت الغروب\n"
                                                      "ياسين كيضحك وكيشير للسما\n"
                                                      "(إلا ذكرتي سمية، غير هي اللي كتبان فداك المشهد)")
                    st_mode = gr.Radio(STORY_MODES, value=STORY_MODES[0], label="🎬 نوع القصة")
                    st_aspect = gr.Radio(ASPECTS, value=ASPECTS[0], label="📐 الشكل")
                    st_go = gr.Button("🎬 صاوب القصة", elem_classes="gen-btn", elem_id="st_go")
                av_state = gr.State(None)

        mode.change(lambda m: [gr.update(visible=m == x) for x in MODES], mode,
                    [g_img, g_txt, g_swap, g_face, g_story])

        duration = gr.Radio(DURATIONS, value=10, label="⏱️ المدة (ثواني)")
        quality = gr.Radio([Q_HIGH, Q_FAST], value=Q_HIGH, label="🎞️ الجودة",
                           info="العالية أوضح ولكن أبطأ بزاف (تقريباً 3 مرات). للتجربة الأولى اختار السريعة.")
        with gr.Accordion("⚙️ إعدادات متقدمة", open=False):
            steps = gr.Slider(15, 50, value=QUALITY[Q_HIGH]["steps"], step=1, label="عدد الخطوات (كثر = أدق وأبطأ)")
            guidance = gr.Slider(2.0, 8.0, value=5.0, step=0.5, label="قوة الالتزام بالوصف")
            seed = gr.Number(value=-1, precision=0, label="رقم البذرة (-1 = عشوائي)")
            translate = gr.Checkbox(value=True, label="ترجم الوصف للإنجليزية أوتوماتيكياً (أحسن نتيجة)")
            colorfix = gr.Checkbox(value=True, label="ثبّت الألوان بين القطع")
        quality.change(lambda q: QUALITY[q]["steps"], quality, steps)
        # فالقصة المدة كتجي من عدد السطور
        mode.change(lambda m: gr.update(visible=m != MODES[4]), mode, duration)

        gr.Markdown("### 🎬 إنشائي", rtl=True)
        video = gr.Video(label="آخر فيديو (كيتحدّث مع كل قطعة)", value=latest_video())
        again_btn = gr.Button("🔁 عاود بنفس الإعدادات (نسخة أخرى)", elem_classes="gen-btn")
        files = gr.File(label="⬇️ الفيديوهات ديالك (كليكي باش تحمّل)", file_count="multiple",
                        value=list_videos(), interactive=False)
        with gr.Row():
            refresh = gr.Button("🔄 تحديث")
            stop = gr.Button("⏹️ وقف الطلب")
        off = gr.Button("🔌 طفي التطبيق (باش توفر الساعات)", variant="stop")
        gr.Markdown("ℹ️ تقدر تسد التليفون، الخدمة كتكمل وكيجيك إشعار ملي يوجد الفيديو.", rtl=True)

        shown = gr.State({"video": latest_video(), "files": tuple(list_videos()), "cands": tuple(latest_avatar_cands())})

        def tick(st):
            touch()
            st = dict(st or {})
            v, fl, cs = latest_video(), tuple(list_videos()), tuple(latest_avatar_cands())
            out_v, out_f, out_c = gr.skip(), gr.skip(), gr.skip()
            if v != st.get("video"):
                out_v, st["video"] = v, v
            if fl != st.get("files"):
                out_f, st["files"] = list(fl), fl
            if cs != st.get("cands"):
                out_c, st["cands"] = [(c, f"{k + 1}") for k, c in enumerate(cs)], cs
            return status_md(), out_v, out_f, st, out_c

        def sub_image(img, p, d, q, s, g, sd, tr, cf):
            if img is None:
                return "⚠️ زيد الصورة، ولا استعمل «نص إلى فيديو»."
            return submit(img, p, d, q, ASPECTS[0], s, g, sd, tr, cf)

        def sub_text(p, a, d, q, s, g, sd, tr, cf):
            return submit(None, p, d, q, a, s, g, sd, tr, cf)

        def turn_off():
            threading.Thread(target=shutdown, args=("طفيتيه من الزر.",), daemon=True).start()
            return "🔌 كيطفى… الفيديوهات محفوظين فـ Output ديال Kaggle."

        outs = [status, video, files, shown, av_gal]
        adv = [duration, quality, steps, guidance, seed, translate, colorfix]
        go_i.click(sub_image, [image, prompt_i] + adv, info).then(tick, shown, outs)
        go_t.click(sub_text, [prompt_t, aspect] + adv, info).then(tick, shown, outs)
        stop.click(cancel_all, None, info)
        scan_btn.click(scan_ui, sw_video, [chars_gal, chars_info] + slots)
        go_sw.click(submit_swap, [sw_video, sw_enh, sw_ok] + slots, info).then(tick, shown, outs)
        go_fa.click(lambda f, p, a, d, q, s, g, sd, tr, ok: submit_face_ai(f, p, a, d, q, s, g, sd, tr, ok),
                    [fa_face, fa_prompt, fa_aspect, duration, quality, steps, guidance, seed, translate, fa_ok],
                    info).then(tick, shown, outs)
        again_btn.click(again, None, info).then(tick, shown, outs)

        def pick_cand(gal, evt: gr.SelectData):
            return _pick(_gal_path(gal, evt))

        def after_save(av, name):
            msg, card, saved, st = save_avatar(av, name)
            return msg, card, saved, st, gr.update(choices=cast_names())

        def after_upload(f):
            msg, saved = upload_avatar(f)
            return msg, saved, gr.update(choices=cast_names())

        av_src.change(lambda v: (gr.update(visible=v.startswith("📷")), gr.update(visible=not v.startswith("📷"))),
                      av_src, [g_av_photo, g_av_desc])
        toon_btn.click(cartoonize_ui, [av_photo, av_gender, av_ok], [av_gal, av_info])
        av_go.click(submit_avatar, [av_gender, av_style, av_desc, quality, steps, guidance, seed, translate],
                    av_info).then(tick, shown, outs)
        av_gal.select(pick_cand, av_gal, [av_state, av_cur, av_info])
        av_saved.select(pick_cand, av_saved, [av_state, av_cur, av_info])
        av_save.click(after_save, [av_state, av_name], [av_info, av_card, av_saved, av_state, st_cast])
        av_up.upload(after_upload, av_up, [av_info, av_saved, st_cast])
        st_go.click(submit_story, [st_cast, st_story, st_mode, st_aspect, quality, steps, guidance, seed, translate],
                    info).then(tick, shown, outs)
        off.click(turn_off, None, info)
        refresh.click(tick, shown, outs)
        gr.Timer(8).tick(tick, shown, outs)
        demo.load(tick, shown, outs)
    return demo


# ----------------------------------------------------------------------------
# الرابط العام (Gradio، وإلا Cloudflare كاحتياط)
# ----------------------------------------------------------------------------
TRY_CF = re.compile(r"https://(?!api\.)[a-z0-9]+(?:-[a-z0-9]+)+\.trycloudflare\.com")  # ماشي رسائل الخطأ ديال api.


def cloudflare_tunnel(port, timeout=90):
    exe = "/tmp/cloudflared"
    if not os.path.exists(exe):
        import urllib.request

        urllib.request.urlretrieve(
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64", exe)
        os.chmod(exe, 0o755)
    p = subprocess.Popen([exe, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    found = {}

    def reader():
        for line in p.stdout:
            m = TRY_CF.search(line)
            if m and "url" not in found:
                found["url"] = m.group(0)

    threading.Thread(target=reader, daemon=True).start()
    t = time.time()
    while "url" not in found and time.time() - t < timeout and p.poll() is None:
        time.sleep(0.5)
    return found.get("url")


def _face_autoload():
    while not ENGINE.ready and ENGINE.error is None:
        time.sleep(5)
    FACES.load()
    try:  # أدوات الكرتون (34 MB + 176 MB) كيتنزلو من دابا باش ما تتسناش فأول ضغطة
        for name in TOON_STYLES:
            TOON.net(name)
        TOON.mask(Image.new("RGB", (64, 64)))
        log("toon tools ready")
    except Exception as e:
        log("toon preload failed (غادي يتعاود ملي تحتاجهم):", e)


def start_background(components=None):
    os.makedirs(OUT_DIR, exist_ok=True)
    if os.environ.get("FACE_AUTOLOAD", "1") == "1":
        threading.Thread(target=_face_autoload, daemon=True).start()
    threading.Thread(target=ENGINE.load, kwargs={"components": components}, daemon=True).start()
    threading.Thread(target=worker, daemon=True).start()


def main():
    start_background()
    demo = build_ui()
    demo.queue(default_concurrency_limit=4)
    # إلا ما خدمش الرابط ديال Gradio كيرجع None (بلا ما يطيح)، وكنجربو Cloudflare
    _, local_url, url = demo.launch(share=os.environ.get("VIDEO_APP_SHARE", "1") == "1", prevent_thread_lock=True,
                                    allowed_paths=[OUT_DIR], css=CSS, theme=make_theme(), head=HEAD,
                                    footer_links=[], show_error=True, server_port=PORT)
    if not url and os.environ.get("VIDEO_APP_SHARE", "1") == "1" and os.environ.get("VIDEO_APP_CF", "1") == "1":
        log("Gradio share failed → trying Cloudflare tunnel")
        try:
            url = cloudflare_tunnel(PORT)
        except Exception as e:
            log("cloudflare failed:", e)
    if url:
        url = url.rstrip("/") + "/?__theme=dark"
        STATE["url"] = url
        notify("🔗 التطبيق خدام", "كليكي هنا باش تحل التطبيق. (الموديل كيتحمّل، كيجيك إشعار ملي يوجد)", url, ["link"], 4)
    bar = "=" * 60
    print(f"\n{bar}\n🔗 الرابط ديال التطبيق (حلّو فالتليفون):\n\n    {url or '❌ ما قدرتش نصاوب رابط عام'}\n")
    if NTFY_TOPIC:
        print(f"📌 الرابط الثابت ديالك (ديما فيه آخر رابط):  https://ntfy.sh/{NTFY_TOPIC}\n")
    print(f"كيطفى بوحدو إلا ما تستعملش {int(IDLE_MINUTES)} دقيقة (من بعد ما يوجد الموديل).\n{bar}\n", flush=True)
    threading.Thread(target=idle_watchdog, daemon=True).start()
    demo.block_thread()


if __name__ == "__main__":
    main()
