import { defineComponent, h } from 'vue'

export const commonStubs = {
  ElCard: {
    name: 'ElCard',
    inheritsAttrs: true,
    template:
      '<div class="el-card-stub" v-bind="$attrs"><slot name="header"></slot><slot></slot></div>',
  },
  ElButton: {
    name: 'ElButton',
    props: ['type', 'size', 'link', 'loading', 'disabled', 'plain'],
    emits: ['click'],
    template: '<button @click="$emit(\'click\')"><slot></slot></button>',
  },
  ElInput: {
    name: 'ElInput',
    props: ['modelValue', 'placeholder', 'type', 'clearable', 'disabled', 'size'],
    emits: ['update:modelValue', 'change', 'blur', 'focus'],
    template:
      '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
  ElSelect: {
    name: 'ElSelect',
    props: ['modelValue', 'placeholder', 'clearable', 'disabled', 'size'],
    emits: ['update:modelValue', 'change'],
    template:
      '<select class="el-select-stub" :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><slot></slot></select>',
  },
  ElOption: {
    name: 'ElOption',
    props: ['label', 'value'],
    template: '<option :value="value">{{ label }}</option>',
  },
  ElTable: {
    name: 'ElTable',
    props: ['data', 'border', 'stripe', 'rowKey'],
    emits: ['selection-change'],
    template: '<div class="el-table-stub"><slot></slot></div>',
  },
  ElTableColumn: {
    name: 'ElTableColumn',
    props: ['type', 'width', 'prop', 'label', 'fixed'],
    template: '<div class="el-table-col-stub"><slot></slot></div>',
  },
  ElPagination: {
    name: 'ElPagination',
    props: ['total', 'pageSize', 'currentPage', 'background', 'layout'],
    emits: ['size-change', 'current-change'],
    template: '<div class="el-pagination-stub"></div>',
  },
  ElDialog: {
    name: 'ElDialog',
    props: ['modelValue', 'title', 'width'],
    emits: ['update:modelValue', 'close'],
    template: '<div class="el-dialog-stub"><slot></slot><slot name="footer"></slot></div>',
  },
  ElForm: {
    name: 'ElForm',
    props: ['model', 'labelWidth', 'size', 'rules'],
    setup(_, { expose }) {
      expose({ validate: () => Promise.resolve(), resetFields: () => {} })
    },
    template: '<form class="el-form-stub"><slot></slot></form>',
  },
  ElFormItem: {
    name: 'ElFormItem',
    props: ['prop', 'label'],
    template: '<div class="el-form-item-stub"><slot></slot></div>',
  },
  ElTag: {
    name: 'ElTag',
    props: ['type', 'size'],
    template: '<span class="el-tag-stub"><slot></slot></span>',
  },
  ElIcon: {
    name: 'ElIcon',
    props: ['size', 'color'],
    template: '<span class="el-icon-stub"><slot></slot></span>',
  },
  ElSpace: {
    name: 'ElSpace',
    props: ['direction', 'size'],
    template: '<div class="el-space-stub"><slot></slot></div>',
  },
  ElBadge: {
    name: 'ElBadge',
    props: ['value', 'hidden', 'max'],
    template: '<div class="el-badge-stub"><slot></slot></div>',
  },
  ElAvatar: {
    name: 'ElAvatar',
    props: ['size'],
    template: '<div class="el-avatar-stub"><slot></slot></div>',
  },
  ElDropdown: {
    name: 'ElDropdown',
    props: ['command'],
    emits: ['command'],
    template: '<div class="el-dropdown-stub"><slot></slot><slot name="dropdown"></slot></div>',
  },
  ElDropdownMenu: {
    name: 'ElDropdownMenu',
    template: '<div class="el-dropdown-menu-stub"><slot></slot></div>',
  },
  ElDropdownItem: {
    name: 'ElDropdownItem',
    props: ['command'],
    emits: ['click'],
    template: '<div class="el-dropdown-item-stub" @click="$emit(\'click\')"><slot></slot></div>',
  },
  ElMenu: {
    name: 'ElMenu',
    props: [
      'mode',
      'router',
      'defaultActive',
      'collapse',
      'backgroundColor',
      'textColor',
      'activeTextColor',
    ],
    template: '<div class="el-menu-stub"><slot></slot></div>',
  },
  ElMenuItem: {
    name: 'ElMenuItem',
    props: ['index'],
    template: '<div class="el-menu-item-stub"><slot></slot></div>',
  },
  ElSubMenu: {
    name: 'ElSubMenu',
    props: ['index'],
    template: '<div class="el-sub-menu-stub"><slot name="title"></slot><slot></slot></div>',
  },
  ElContainer: {
    name: 'ElContainer',
    template: '<div class="el-container-stub"><slot></slot></div>',
  },
  ElAside: {
    name: 'ElAside',
    props: ['width'],
    template: '<div class="el-aside-stub"><slot></slot></div>',
  },
  ElHeader: { name: 'ElHeader', template: '<div class="el-header-stub"><slot></slot></div>' },
  ElMain: { name: 'ElMain', template: '<div class="el-main-stub"><slot></slot></div>' },
  ElAlert: {
    name: 'ElAlert',
    props: ['title', 'type', 'closable'],
    template: '<div class="el-alert-stub"><slot></slot></div>',
  },
  ElEmpty: {
    name: 'ElEmpty',
    props: ['description'],
    template: '<div class="el-empty-stub">{{ description }}</div>',
  },
  ElLoading: { name: 'ElLoading', template: '<div class="el-loading-stub"></div>' },
  ElProgress: {
    name: 'ElProgress',
    props: ['percentage', 'status'],
    template: '<div class="el-progress-stub"></div>',
  },
  ElSwitch: {
    name: 'ElSwitch',
    props: ['modelValue', 'activeText', 'inactiveText'],
    emits: ['update:modelValue', 'change'],
    template:
      '<button class="el-switch-stub" @click="$emit(\'update:modelValue\', !modelValue)">{{ modelValue ? "开" : "关" }}</button>',
  },
  ElRadioGroup: {
    name: 'ElRadioGroup',
    props: ['modelValue'],
    emits: ['update:modelValue', 'change'],
    template: '<div class="el-radio-group-stub"><slot></slot></div>',
  },
  ElRadio: {
    name: 'ElRadio',
    props: ['label', 'value'],
    template: '<label class="el-radio-stub"><slot></slot></label>',
  },
  ElCheckbox: {
    name: 'ElCheckbox',
    props: ['modelValue', 'label'],
    emits: ['update:modelValue', 'change'],
    template: '<label class="el-checkbox-stub"><slot></slot></label>',
  },
  ElDatePicker: {
    name: 'ElDatePicker',
    props: ['modelValue', 'type', 'placeholder'],
    emits: ['update:modelValue', 'change'],
    template: '<input class="el-date-picker-stub" type="date" />',
  },
  ElTree: {
    name: 'ElTree',
    props: ['data', 'props', 'nodeKey'],
    emits: ['node-click'],
    template: '<div class="el-tree-stub"><slot></slot></div>',
  },
  ElTabs: {
    name: 'ElTabs',
    props: ['modelValue', 'type'],
    emits: ['update:modelValue', 'tab-change'],
    template: '<div class="el-tabs-stub"><slot></slot></div>',
  },
  ElTabPane: {
    name: 'ElTabPane',
    props: ['label', 'name'],
    template: '<div class="el-tab-pane-stub"><slot></slot></div>',
  },
  ElTooltip: {
    name: 'ElTooltip',
    props: ['content', 'placement'],
    template: '<div class="el-tooltip-stub"><slot></slot></div>',
  },
  ElPopover: {
    name: 'ElPopover',
    props: ['title', 'content', 'placement'],
    template: '<div class="el-popover-stub"><slot></slot></div>',
  },
  ElDivider: { name: 'ElDivider', template: '<div class="el-divider-stub"></div>' },
  ElRow: {
    name: 'ElRow',
    props: ['gutter'],
    template: '<div class="el-row-stub"><slot></slot></div>',
  },
  ElCol: {
    name: 'ElCol',
    props: ['span', 'offset'],
    template: '<div class="el-col-stub"><slot></slot></div>',
  },
  ElStatistic: {
    name: 'ElStatistic',
    props: ['title', 'value'],
    template: '<div class="el-statistic-stub"><slot></slot></div>',
  },
  ElDescriptions: {
    name: 'ElDescriptions',
    props: ['title', 'column'],
    template: '<div class="el-descriptions-stub"><slot></slot></div>',
  },
  ElDescriptionsItem: {
    name: 'ElDescriptionsItem',
    props: ['label'],
    template: '<div class="el-descriptions-item-stub"><slot></slot></div>',
  },
  ElTimeline: { name: 'ElTimeline', template: '<div class="el-timeline-stub"><slot></slot></div>' },
  ElTimelineItem: {
    name: 'ElTimelineItem',
    props: ['timestamp'],
    template: '<div class="el-timeline-item-stub"><slot></slot></div>',
  },
  ElImage: {
    name: 'ElImage',
    props: ['src', 'fit'],
    template: '<div class="el-image-stub"></div>',
  },
  ElLink: {
    name: 'ElLink',
    props: ['type', 'href'],
    emits: ['click'],
    template: '<a class="el-link-stub" @click="$emit(\'click\')"><slot></slot></a>',
  },
  ElText: {
    name: 'ElText',
    props: ['type', 'size'],
    template: '<span class="el-text-stub"><slot></slot></span>',
  },
  ElMessageBox: { name: 'ElMessageBox' },
  ElNotification: { name: 'ElNotification' },
}

export const iconStubs = [
  'ArrowLeft',
  'ArrowRight',
  'WarningFilled',
  'Fold',
  'Expand',
  'Headset',
  'Bell',
  'User',
  'Lock',
  'Search',
  'Refresh',
  'Plus',
  'Delete',
  'Edit',
  'View',
  'Download',
  'Upload',
  'Setting',
  'UserFilled',
  'Monitor',
  'Document',
  'DataLine',
  'Service',
  'Ticket',
  'Money',
  'Check',
  'Close',
  'InfoFilled',
  'SuccessFilled',
  'CircleCheck',
  'Loading',
  'More',
  'Star',
  'StarFilled',
  'ChatDotRound',
  'Promotion',
].reduce(
  (acc, name) => {
    acc[name] = defineComponent({ name, render: () => h('span', name) })
    return acc
  },
  {} as Record<string, any>
)

export function mockElementPlus() {
  return {
    ElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
    ElMessageBox: {
      confirm: vi.fn(() => Promise.resolve()),
      alert: vi.fn(() => Promise.resolve()),
    },
    ElNotification: vi.fn(),
  }
}
