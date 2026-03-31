import { Router, type IRouter } from "express";
import healthRouter from "./health.js";
import bimRouter from "./bim/index.js";

const router: IRouter = Router();

router.use(healthRouter);
router.use("/bim", bimRouter);

export default router;
