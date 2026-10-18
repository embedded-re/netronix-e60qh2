/* SPDX-License-Identifier: GPL-2.0+ */
/* Copyright (C) 2020 Andreas Kemnade */
int mxc_epdc_send_single_update(struct drm_rect *clip, int pitch,
				void *vaddr,
                                struct mxc_epdc *priv);
int mxc_epdc_send_update(struct drm_rect *clip, int pitch, void *vaddr,
			 struct mxc_epdc *priv, u32 waveform_mode, u32 update_mode);
void mxc_epdc_draw_mode0(struct mxc_epdc *priv);
int mxc_epdc_init_update(struct mxc_epdc *priv);
void mxc_epdc_flush_updates(struct mxc_epdc *priv);
bool mxc_epdc_updates_idle(struct mxc_epdc *priv);
