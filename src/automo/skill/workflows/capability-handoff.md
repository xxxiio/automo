# Capability handoff workflow

When valid research requires missing software capability, stop the experiment and persist a bounded capability request. Do not implement the capability ad hoc inside the research workflow. If GetDone integration is enabled, hand off only the implementation contract and allowed file scope. GetDone owns `.agent/`; Automo owns `.automo/`. After implementation, Automo independently validates the capability result before resuming the unchanged research hypothesis and evidence boundary.
