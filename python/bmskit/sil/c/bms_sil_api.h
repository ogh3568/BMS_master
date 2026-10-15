/*
 * bms_sil_api.h - thin C ABI between the user's C model and bmskit (SIL).
 *
 * The user's model code is NOT modified. A small glue file implements
 * reset/step/outputs by calling the existing model functions, and the parameter
 * table is generated from the extracted registry (python -m bmskit.sil.wrapgen).
 * Build the model sources + glue + generated table as a shared library and load
 * it with bmskit.sil.runner.SilModel.
 *
 * Conventions: SI units, current in A with discharge positive, temperature in degC.
 */
#ifndef BMS_SIL_API_H
#define BMS_SIL_API_H

#ifdef _WIN32
#define BMS_SIL_EXPORT __declspec(dllexport)
#else
#define BMS_SIL_EXPORT __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define BMS_SIL_API_VERSION 1

/* ---- implemented by the generated parameter table (bms_sil_params.c) ---- */
BMS_SIL_EXPORT int bms_sil_api_version(void);
BMS_SIL_EXPORT int bms_sil_param_count(void);
BMS_SIL_EXPORT const char *bms_sil_param_name(int idx);
BMS_SIL_EXPORT int bms_sil_get_param(const char *name, double *value); /* 0 ok, -1 unknown */
BMS_SIL_EXPORT int bms_sil_set_param(const char *name, double value);  /* 0 ok, -1 unknown */

/* ---- implemented by the hand-written glue (one small file per model) ---- */
BMS_SIL_EXPORT int bms_sil_reset(double soc0, double temp_c);                     /* re-init states */
BMS_SIL_EXPORT int bms_sil_step(double dt_s, double current_a, double temp_c);    /* advance dt */
BMS_SIL_EXPORT int bms_sil_output_count(void);
BMS_SIL_EXPORT const char *bms_sil_output_name(int idx); /* e.g. "v", "soc", "x_surf_n" */
BMS_SIL_EXPORT double bms_sil_get_output(int idx);

#ifdef __cplusplus
}
#endif
#endif /* BMS_SIL_API_H */
