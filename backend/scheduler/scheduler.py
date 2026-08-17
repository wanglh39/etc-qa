from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from utils.config import get_config
from utils.logger import get_logger

logger = get_logger("scheduler.manager")


class SchedulerManager:
    def __init__(self):
        self._scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        self._started = False
        self._task_stats: dict[str, dict] = {}

    def start(self):
        if self._started:
            logger.warning("调度器已在运行")
            return
        cfg = get_config().get("scheduler", {})
        if not cfg.get("enabled", True):
            logger.info("调度器未启用(scheduler.enabled=false)")
            return

        tz = cfg.get("timezone", "Asia/Shanghai")
        self._scheduler = BackgroundScheduler(timezone=tz)

        jobs_cfg = cfg.get("jobs", {})
        self._add_job("sync_and_ingest", jobs_cfg.get("sync_and_ingest", {}))
        self._add_job("cleanup", jobs_cfg.get("cleanup", {}))
        self._add_job("alert_check", jobs_cfg.get("alert_check", {}))

        self._scheduler.start()
        self._started = True
        logger.info("调度器已启动")

    def stop(self):
        if not self._started:
            return
        self._scheduler.shutdown(wait=False)
        self._started = False
        logger.info("调度器已停止")

    def is_running(self) -> bool:
        return self._started

    def get_status(self) -> dict:
        jobs = []
        if self._started:
            for job in self._scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                })
        return {
            "running": self._started,
            "jobs": jobs,
            "task_stats": self._task_stats,
        }

    def trigger_job(self, job_id: str) -> dict:
        if not self._started:
            return {"error": "调度器未运行"}
        job = self._scheduler.get_job(job_id)
        if job is None:
            return {"error": f"任务 {job_id} 不存在"}
        job.modify(next_run_time=datetime.now())
        logger.info(f"手动触发任务: {job_id}")
        return {"message": f"任务 {job_id} 已触发"}

    def update_job_schedule(self, job_id: str, hours: int = None, minutes: int = None) -> dict:
        if not self._started:
            return {"error": "调度器未运行"}
        job = self._scheduler.get_job(job_id)
        if job is None:
            return {"error": f"任务 {job_id} 不存在"}

        kwargs = {}
        if hours is not None and hours > 0:
            kwargs["hours"] = hours
        if minutes is not None and minutes > 0:
            kwargs["minutes"] = minutes
        if not kwargs:
            return {"error": "必须提供hours或minutes参数"}

        trigger = IntervalTrigger(**kwargs)
        self._scheduler.add_job(
            func=job.func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=60,
        )
        logger.info(f"任务 {job_id} 调度已更新: {trigger}")
        return {"message": f"任务 {job_id} 调度已更新为 {trigger}"}

    def _add_job(self, job_id: str, job_cfg: dict):
        if not job_cfg.get("enabled", True):
            logger.info(f"任务 {job_id} 未启用，跳过")
            return

        from scheduler import tasks
        func_map = {
            "sync_and_ingest": tasks.sync_and_ingest_task,
            "cleanup": tasks.cleanup_task,
            "alert_check": tasks.alert_check_task,
        }
        func = func_map.get(job_id)
        if func is None:
            logger.warning(f"未知任务: {job_id}")
            return

        schedule_type = job_cfg.get("schedule_type", "interval")
        trigger = None
        if schedule_type == "interval":
            kwargs = {}
            if "hours" in job_cfg:
                kwargs["hours"] = job_cfg["hours"]
            if "minutes" in job_cfg:
                kwargs["minutes"] = job_cfg["minutes"]
            if "seconds" in job_cfg:
                kwargs["seconds"] = job_cfg["seconds"]
            if not kwargs:
                kwargs["hours"] = 1
            trigger = IntervalTrigger(**kwargs)
        else:
            logger.warning(f"不支持的调度类型: {schedule_type}，使用默认1小时间隔")
            trigger = IntervalTrigger(hours=1)

        max_retries = job_cfg.get("max_retries", 3)
        self._scheduler.add_job(
            func=func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=60,
        )
        logger.info(f"已添加任务: {job_id}, 触发器={trigger}, max_retries={max_retries}")