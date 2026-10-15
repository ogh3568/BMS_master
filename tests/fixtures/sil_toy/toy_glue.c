/* TEST FIXTURE glue: maps bms_sil_api.h reset/step/outputs onto the toy model functions. */
#include "bms_sil_api.h"
void toy_reset(double soc0, double temp_c);
void toy_step(double dt, double i, double temp_c);
double toy_voltage(void);
double toy_soc(void);

static const char *k_outputs[] = { "v", "soc" };

int bms_sil_reset(double soc0, double temp_c) { toy_reset(soc0, temp_c); toy_step(0.0, 0.0, temp_c); return 0; }
int bms_sil_step(double dt_s, double current_a, double temp_c) { toy_step(dt_s, current_a, temp_c); return 0; }
int bms_sil_output_count(void) { return 2; }
const char *bms_sil_output_name(int idx) { return (idx >= 0 && idx < 2) ? k_outputs[idx] : 0; }
double bms_sil_get_output(int idx) { return idx == 0 ? toy_voltage() : toy_soc(); }
