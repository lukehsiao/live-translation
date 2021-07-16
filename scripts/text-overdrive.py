import obspython as obs


class State:
    def __init__(self):
        # Source name and caption file must match what is used in OBS and by the CLI.
        self.source_name = "captions"
        self.captionfile = open("/path/to/repo/captions.txt", "r")
        self.line = None
        self.counter = 0
        self.divider = 10

    def tick(self):
        # To lessen the CPU load, only update once every self.divider frames
        self.counter += 1
        if self.counter % self.divider:
            return self.line

        self.counter = 0

        nextlines = self.captionfile.readline().split("~^~")
        if nextlines[0]:
            # Only look at the last 4 lines, assuming the previous are stable
            self.line = "\n".join(nextlines[-4:])
            print(self.line)

        return self.line

    def set_name(self, name):
        self.source_name = name


state = State()


def script_description():
    return "Select a text source to force an update every frame instead of each second."


def script_update(settings):
    name = obs.obs_data_get_string(settings, "source")
    print(f"Updating source_name: {name}")
    state.set_name(name)


def script_properties():
    props = obs.obs_properties_create()
    p = obs.obs_properties_add_list(
        props,
        "source",
        "Text Source",
        obs.OBS_COMBO_TYPE_EDITABLE,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    sources = obs.obs_enum_sources()
    print(f"{sources}")
    for _, source in enumerate(sources):
        source_id = obs.obs_source_get_id(source)
        print(f"{source_id}")
        if (
            source_id == "text_gdiplus"
            or source_id == "text_ft2_source_v2"
            or source_id == "text_pango_source"
        ):
            name = obs.obs_source_get_name(source)
            obs.obs_property_list_add_string(p, name, name)
            print("name")

    obs.source_list_release(sources)

    return props


def script_tick(seconds):
    if state.source_name is None:
        return

    source = obs.obs_get_source_by_name(state.source_name)
    if source is None:
        print("No source.")
        return

    text = state.tick()
    settings = obs.obs_source_get_settings(source)
    obs.obs_data_set_string(settings, "text", text)
    obs.obs_source_update(source, settings)
    obs.obs_data_release(settings)
    obs.obs_source_release(source)