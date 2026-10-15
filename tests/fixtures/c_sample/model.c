/* Test fixture only. */
#include "model_params.h"

static const ModelParam_t g_param = { .Ds_p = 4.0e-15f, .k_n = 6.48e-7f, .R0 = 0.02f, .x100 = 0.9f };
const float OCV_TBL[3][2] = { {0.0f, 3.0f}, {0.5f, 3.7f}, {1.0f, 4.2f} };
float g_soc_gain = 0.05f;
static const float r_sei_n = 0.003;

float model_voltage(float i, float t)
{
    float ds = DS_NEG_REF * (1.0f + EA_DS_NEG * 0.0f);
    float v = OCV_TBL[1][1] - i * g_param.R0 - i * r_sei_n;
    v -= 0.0123f * i;              /* hidden empirical correction */
    return v + g_soc_gain * ds;
}

int uv_check(float v_mv) { return v_mv < UV_THRESH_MV; }
