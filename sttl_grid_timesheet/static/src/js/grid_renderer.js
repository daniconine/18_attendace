/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { View } from "@web/views/view";
import { Field } from "@web/views/fields/field";
import { Record } from "@web/model/record";
import { useService } from "@web/core/utils/hooks";
import { ViewScaleSelector } from "@web/views/view_components/view_scale_selector";
import { user } from "@web/core/user";

export class GridRenderer extends Component {

    async setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            user: user,
            groupedData: [],
            scale: 'week',
            dateColumns: [],
            referenceDate: new Date(),
            isWizardOpen: false,
            wizardData: {
                project_id: '',
                task_id: '',
                name: '',
                date: '',
                unit_amount: '00:00',
            },
            timerRunning: false,
            elapsedTime: 0,
            timerInterval: null,
            selectedProjectId: '',
            selectedTaskId: '',
            projectsForTimer: [],
            tasksForTimer: [],
            projectSelected: false,
            rowTimers: {},
            wizardTimerData: {
                description: '',
                show: false,
                taskId: null,
                projectId: null,
                elapsedTime: 0
            },
            searchTerm: '',
            originalGroupedData: [],
            employees: [],
            selectedEmployeeUserId: '',

            projectSearchText: '',
            showProjectDropdown: false,
            filteredProjects: [],
            taskSearchText: '',
            showTaskDropdown: false,
            filteredTasks: [],

            groupByProject: true,
            expandedProjects: {},
        });

        onWillStart(async () => {
            if (sessionStorage.getItem('referenceDate')) {
                const storedDate = sessionStorage.getItem('referenceDate');
                this.state.referenceDate = storedDate ? new Date(storedDate) : new Date();
            }
            if (sessionStorage.getItem('selectedEmployeeUserId')) {
                this.state.selectedEmployeeUserId = sessionStorage.getItem('selectedEmployeeUserId');
            }
            if (sessionStorage.getItem('scale')) {
                this.state.scale = sessionStorage.getItem('scale');
            }
            this.getDateColumns();
            await this.loadEmployees();
            await this.fetchTimesheets();
        });
    }

    computeDailyProjectTotal(dateKey) {
        if (this.state.groupByProject) {
            return this.state.groupedData.reduce((sum, project) => {
                return sum + project.tasks.reduce((taskSum, task) => {
                    return taskSum + ((task.timesheets && task.timesheets[dateKey]) || 0);
                }, 0);
            }, 0);
        } else {
            return this.state.groupedData.reduce((sum, line) => {
                return sum + ((line.timesheets && line.timesheets[dateKey]) || 0);
            }, 0);
        }
    }

    toggleGroupByProject() {
        this.state.groupByProject = !this.state.groupByProject;
        if (!this.state.groupByProject) {
            this.state.expandedProjects = {};
        }
    }

    toggleProjectExpansion(projectId) {
        this.state.expandedProjects = {
            ...this.state.expandedProjects,
            [projectId]: !this.state.expandedProjects[projectId]
        };
    }

    isProjectExpanded(projectId) {
        return this.state.expandedProjects[projectId] || false;
    }

    async onProjectSearchChange(ev) {
        this.state.projectSearchText = ev.target.value;
        if (this.state.projectSearchText.length == 0) {
            this.state.filteredProjects = this.state.projectsForTimer;
            this.state.selectedProjectId = '';
            return;
        }
        if (this.state.selectedProjectId) {
            const selectedProject = this.state.projectsForTimer.find(
                proj => proj.id === this.state.selectedProjectId
            );

            if (selectedProject && selectedProject.name.toLowerCase() != this.state.projectSearchText.toLowerCase()) {
                this.state.filteredTasks = []
                this.state.selectedProjectId = '';
            }
            else if(selectedProject) {
                this.state.filteredProjects = this.state.projectsForTimer;
                return;
            }
        }
        const searchTerm = this.state.projectSearchText.toLowerCase();
        this.state.filteredProjects = this.state.projectsForTimer.filter(proj =>
            proj.name.toLowerCase().includes(searchTerm)
        );
    }

    onProjectInputFocus() {
        this.state.showProjectDropdown = true;
        if (this.state.projectSearchText.length > 0) {
            this.onProjectSearchChange({ target: { value: this.state.projectSearchText } });
        }
    }

    onProjectInputBlur() {
        setTimeout(() => {
            this.state.showProjectDropdown = false;
        }, 200);
    }

    onProjectSelect(project) {
        this.state.selectedProjectId = project.id;
        this.state.projectSearchText = project.name;
        this.state.taskSearchText = "";
        this.state.showProjectDropdown = false;
        this.onTimerProjectChange({ target: { value: project.id } });
    }

    async onTaskSearchChange(ev) {
        this.state.taskSearchText = ev.target.value;
        if (this.state.taskSearchText.length == 0) {
            this.state.filteredTasks = this.state.tasksForTimer;
            this.state.selectedTaskId = '';
            return;
        }
        if (this.state.selectedTaskId) {
            const selectedTask = this.state.tasksForTimer.find(
                proj => proj.id === this.state.selectedTaskId
            );
            if (selectedTask && selectedTask.name.toLowerCase() != this.state.taskSearchText.toLowerCase()) {
                this.state.selectedTaskId = '';
            }
            else if(selectedTask) {
                this.state.filteredTasks = this.state.tasksForTimer;
                return;
            }
        }
        const searchTerm = this.state.taskSearchText.toLowerCase();
        this.state.filteredTasks = this.state.tasksForTimer.filter(task =>
            task.name.toLowerCase().includes(searchTerm)
        );
    }

    onTaskInputFocus() {
        this.state.showTaskDropdown = true;
        if (this.state.taskSearchText.length > 0) {
            this.onTaskSearchChange({ target: { value: this.state.taskSearchText } });
        }
    }

    onTaskInputBlur() {
        setTimeout(() => {
            this.state.showTaskDropdown = false;
        }, 200);
    }

    onTaskSelect(task) {
        this.state.selectedTaskId = task.id;
        this.state.taskSearchText = task.name;
        this.state.showTaskDropdown = false;
    }

    async loadEmployees() {
        if (this.state.user.isAdmin) {
            this.state.employees = await this.orm.searchRead(
                "hr.employee",
                [],
                ["id", "name", "user_id"]
            );
        }
    }

    async onEmployeeChange(ev) {
        this.state.selectedEmployeeUserId = ev.target.value;
        sessionStorage.setItem('selectedEmployeeUserId', this.state.selectedEmployeeUserId);

        await this.fetchTimesheets();
    }

    onSearchKeyUp(ev) {
        if (ev.key === 'Enter' || this.state.searchTerm.length >= 3 || this.state.searchTerm.length === 0) {
            this.applySearchFilter();
        }
    }

    applySearchFilter() {
        if (!this.state.searchTerm) {
            this.state.groupedData = [...this.state.originalGroupedData];
            return;
        }

        const searchTerm = this.state.searchTerm.toLowerCase();

        if (this.state.groupByProject) {
            this.state.groupedData = this.state.originalGroupedData.filter(project =>
                project.project_name && project.project_name.toLowerCase().includes(searchTerm)
            );
        } else {
            this.state.groupedData = this.state.originalGroupedData.filter(item =>
                (item.task_name && item.task_name.toLowerCase().includes(searchTerm)) ||
                (item.project_name && item.project_name.toLowerCase().includes(searchTerm))
            );
        }
    }


    clearSearch() {
        this.state.searchTerm = '';
        this.state.groupedData = [...this.state.originalGroupedData];
    }

    onMagnifyClick(ev) {
        const cell = ev.currentTarget.closest('td');
        if (!cell) return;

        const input = cell.querySelector('input');
        if (!input) return;

        const taskId = parseInt(input.dataset.taskId);
        const date = input.dataset.date;

        let taskData;
        let projectId;

        if (this.state.groupByProject) {
            for (const project of this.state.groupedData) {
                const foundTask = project.tasks.find(t => t.task_id === taskId);
                if (foundTask) {
                    taskData = foundTask;
                    projectId = project.project_id;
                    break;
                }
            }
        } else {
            taskData = this.state.groupedData.find(t => t.task_id === taskId);
            projectId = taskData?.project_id;
        }

        if (!taskData) return;

        const domain = [
            ['task_id', '=', taskId],
            ['date', '=', date]
        ];

        if (projectId) {
            domain.push(['project_id', '=', projectId]);
        }

        if (this.state.user.isAdmin && this.state.selectedEmployeeUserId) {
            domain.push(["user_id", "=", parseInt(this.state.selectedEmployeeUserId)]);
        } else if (!this.state.user.isAdmin) {
            domain.push(["user_id", "=", this.state.user.userId]);
        }

        this.actionService.doAction({
            name: "Timesheet Entries",
            type: 'ir.actions.act_window',
            res_model: 'account.analytic.line',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
            domain: domain,
            context: {
                default_task_id: taskId,
                default_project_id: projectId || false,
                default_date: date,
                search_default_group_by_task: 1,
                search_default_group_by_project: 1
            }
        });
    }

    isAnyTimerRunning() {
        const anyRowTimerRunning = Object.values(this.state.rowTimers).some(timer => timer.running);
        const mainTimerRunning = this.state.timerRunning;

        return anyRowTimerRunning || mainTimerRunning;
    }

    getRunningTimerTaskId() {
        const runningRowTimer = Object.entries(this.state.rowTimers).find(([_, timer]) => timer.running);
        if (runningRowTimer) {
            return parseInt(runningRowTimer[0]);
        }

        if (this.state.timerRunning) {
            return 'main';
        }

        return null;
    }

    discardMainTimer() {
        if (this.state.timerRunning) {
            clearInterval(this.state.timerInterval);
            this.state.timerRunning = false;
            this.state.elapsedTime = 0;
            this.state.selectedProjectId = '';
            this.state.selectedTaskId = '';
            this.state.projectSelected = false;
        }
        if (this.state.wizardTimerData.show) {
            this.closeTimerWizard();
        }
    }

    discardRowTimer(taskId) {
        if (this.state.rowTimers[taskId]?.running) {
            clearInterval(this.state.rowTimers[taskId].interval);
            this.state.rowTimers[taskId] = {
                running: false,
                elapsed: 0,
                interval: null
            };
        }
        if (this.state.wizardTimerData.show && this.state.wizardTimerData.taskId === taskId) {
            this.closeTimerWizard();
        }
    }

    async toggleRowTimer(taskId) {
        const findTask = (id) => {
            if (this.state.groupByProject) {
                for (const project of this.state.groupedData) {
                    const task = project.tasks.find(t => t.task_id === id);
                    if (task) return { task, projectId: project.project_id };
                }
                return null;
            } else {
                const task = this.state.groupedData.find(t => t.task_id === id);
                return task ? { task, projectId: task.project_id } : null;
            }
        };

        if (!this.state.rowTimers[taskId]?.running && this.isAnyTimerRunning()) {
            const runningTimerId = this.getRunningTimerTaskId();
            let message = "Please pause the current timer before starting a new one.";

            if (runningTimerId === 'main') {
                message = "Please pause the main timer before starting a row timer.";
            } else if (runningTimerId) {
                const runningTask = findTask(runningTimerId);
                message = `Please pause the timer for "${runningTask?.task?.task_name || 'current task'}" before starting a new one.`;
            }

            this.env.services.notification.add(message, { type: "warning" });
            return;
        }

        if (this.state.rowTimers[taskId]?.running) {
            clearInterval(this.state.rowTimers[taskId].interval);
            this.state.rowTimers[taskId].running = false;
            this.state.rowTimers[taskId].interval = null;

            const taskInfo = findTask(taskId);
            if (!taskInfo) return;

            this.state.wizardTimerData = {
                description: '',
                show: true,
                taskId: taskId,
                projectId: taskInfo.projectId || false,
                elapsedTime: this.state.rowTimers[taskId].elapsed
            };
        } else {
            if (!this.state.rowTimers[taskId]) {
                this.state.rowTimers[taskId] = {
                    running: true,
                    elapsed: 0,
                    interval: null
                };
            } else {
                this.state.rowTimers[taskId].running = true;
            }

            this.state.rowTimers[taskId].interval = setInterval(() => {
                this.state.rowTimers[taskId].elapsed += 1;
            }, 1000);
        }
    }

    closeTimerWizard() {
        this.state.wizardTimerData = {
            description: '',
            show: false,
            taskId: null,
            projectId: null,
            elapsedTime: 0
        };
        this.state.projectSelected = false;
        this.state.selectedProjectId = '';
        this.state.selectedTaskId = '';
    }

    async submitTimerTimesheet() {
        const { description, taskId, projectId, elapsedTime } = this.state.wizardTimerData;

        const elapsedMinutes = elapsedTime / 60;
        const unit_amount = elapsedMinutes < 15 ? 0.25 : Math.round((elapsedTime / 3600) * 100) / 100;
        const date = this.formatDateLocal(new Date());

        const payload = {
            name: description || "/",
            unit_amount,
            task_id: taskId,
            project_id: projectId,
            date,
        };

        try {
            await this.orm.create("account.analytic.line", [payload]);
            this.env.services.notification.add("Timesheet entry created from timer.", { type: "success" });

            if (this.state.timerRunning) {
                this.state.selectedProjectId = '';
                this.state.selectedTaskId = '';
                this.state.projectSelected = false;
                this.state.elapsedTime = 0;
                this.state.timerRunning = false;
            } else {
                if (this.state.rowTimers[taskId]) {
                    this.state.rowTimers[taskId].elapsed = 0;
                }
            }

            this.closeTimerWizard();
            await this.fetchTimesheets();
        } catch (err) {
            this.env.services.notification.add("Failed to create timesheet from timer.", { type: "danger" });
            console.error("Error creating timesheet:", err);

            if (this.state.timerRunning) {
                this.state.timerRunning = true;
                this.state.timerInterval = setInterval(() => {
                    this.state.elapsedTime += 1;
                }, 1000);
            } else if (this.state.rowTimers[taskId]) {
                this.state.rowTimers[taskId].running = true;
                this.state.rowTimers[taskId].interval = setInterval(() => {
                    this.state.rowTimers[taskId].elapsed += 1;
                }, 1000);
            }
        }
    }

    async toggleTimer() {
        const findTask = (id) => {
            if (!id) return null;
            if (this.state.groupByProject) {
                for (const project of this.state.groupedData) {
                    const task = project.tasks.find(t => t.task_id === parseInt(id));
                    if (task) return task;
                }
                return null;
            } else {
                return this.state.groupedData.find(t => t.task_id === parseInt(id));
            }
        };

        if (this.state.timerRunning) {
            const { selectedProjectId, selectedTaskId } = this.state;

            if (!selectedProjectId || !selectedTaskId) {
                this.env.services.notification.add("Please select both a project and a task before stopping the timer.", {
                    type: "warning"
                });
                return;
            }

            clearInterval(this.state.timerInterval);
            this.state.timerRunning = false;

            this.state.wizardTimerData = {
                description: '',
                show: true,
                taskId: parseInt(selectedTaskId),
                projectId: parseInt(selectedProjectId),
                elapsedTime: this.state.elapsedTime
            };
        } else {
            if (this.isAnyTimerRunning()) {
                const runningTimerId = this.getRunningTimerTaskId();
                let message = "Please pause the current timer before starting a new one.";

                if (runningTimerId && runningTimerId !== 'main') {
                    const runningTask = findTask(runningTimerId);
                    message = `Please pause the timer for "${runningTask?.task_name || 'current task'}" before starting the main timer.`;
                }

                this.env.services.notification.add(message, { type: "warning" });
                return;
            }

            this.state.projectSearchText = '';
            this.state.taskSearchText = '';
            this.state.elapsedTime = 0;
            this.state.timerRunning = true;

            await this.loadTimerProjects();

            this.state.timerInterval = setInterval(() => {
                this.state.elapsedTime += 1;
            }, 1000);
        }
    }

    formatElapsedTime(seconds) {
        const hrs = String(Math.floor(seconds / 3600)).padStart(2, '0');
        const mins = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
        const secs = String(seconds % 60).padStart(2, '0');
        return `${hrs}:${mins}:${secs}`;
    }

    async loadTimerProjects() {
        this.state.projectsForTimer = await this.orm.searchRead("project.project", [], ["id", "name"]);
        this.state.filteredProjects = this.state.projectsForTimer;
    }

    async onTimerProjectChange(ev) {
        const projectId = parseInt(ev.target.value);
        this.state.selectedProjectId = projectId;
        this.state.selectedTaskId = '';
        this.state.projectSelected = !!projectId;

        let domain = [["project_id", "=", projectId]];

        if (this.state.user.isAdmin && this.state.selectedEmployeeUserId) {
            domain.push(["user_ids", "in", parseInt(this.state.selectedEmployeeUserId)]);
        } else if (!this.state.user.isAdmin) {
            domain.push(["user_ids", "in", this.state.user.userId]);
        }

        this.state.tasksForTimer = await this.orm.searchRead("project.task", domain, ["id", "name"]);
        this.state.filteredTasks = this.state.tasksForTimer;
    }

    getTimerWizardButtonText() {
        return this.state.wizardTimerData.description.trim() ? "Save" : "Save without description";
    }

    formatHours(floatHours) {
        const totalMinutes = Math.round(floatHours * 60);
        const hours = Math.floor(totalMinutes / 60);
        const minutes = totalMinutes % 60;
        return `${hours}:${minutes.toString().padStart(2, '0')}`;
    }

    async handleReferenceDateChange(newDate) {
        sessionStorage.setItem('referenceDate', newDate.toISOString());
        this.state.referenceDate = newDate;
        this.getDateColumns();
        await this.fetchTimesheets();
    }

    async goToday() {
        await this.handleReferenceDateChange(new Date());
    }

    formatDateLocal(date) {
        const year = date.getFullYear();
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    async onUpdateTimesheetHours(ev) {
        const input = ev.target;
        let rawValue = input.value.trim();
        const oldValueStr = input.dataset.oldValue || "0:00";
        const date = input.dataset.date;
        const lineId = parseInt(input.dataset.taskId);

        let hours = 0;
        let minutes = 0;

        try {
            // Clean up
            rawValue = rawValue.toLowerCase().replace(/\s+/g, '');

            // Handle input starting with ":" → treat as minutes (e.g. ":30" => "0:30")
            if (rawValue.startsWith(":")) {
                rawValue = "0" + rawValue;
            }

            // Case 1: Colon-separated format like "1:30", "00:453", ":30"
            if (/^\d{1,4}:\d{1,4}$/.test(rawValue)) {
                const [h, m] = rawValue.split(":").map(Number);
                hours = h;
                minutes = m;
            }
            // Case 2: Decimal hours like "1.5", ".5"
            else if (/^\d*\.?\d+$/.test(rawValue)) {
                const floatHours = parseFloat(rawValue);
                hours = Math.floor(floatHours);
                minutes = Math.round((floatHours - hours) * 60);
            }
            // Case 3: Whole number → treat as total minutes
            else if (/^\d+$/.test(rawValue)) {
                const totalMinutes = parseInt(rawValue, 10);
                hours = Math.floor(totalMinutes / 60);
                minutes = totalMinutes % 60;
            }
            else {
                throw new Error("Invalid format");
            }

            // Normalize minutes > 60
            if (minutes >= 60) {
                hours += Math.floor(minutes / 60);
                minutes = minutes % 60;
            }

        } catch (e) {
            this.env.services.notification.add("Invalid format. Use formats like H:M, :M, HH:MM, H.M", { type: "warning" });
            input.value = oldValueStr;
            return;
        }

        const normalizedTime = `${hours}:${minutes.toString().padStart(2, '0')}`;
        input.value = normalizedTime;

        const newHours = hours + minutes / 60;

        const oldMatch = oldValueStr.match(/^(\d{1,4})(?::(\d{1,4}))?$/) || ["0:00", "0", "0"];
        const oldHours = parseInt(oldMatch[1]) + (oldMatch[2] ? parseInt(oldMatch[2]) : 0) / 60;

        const diff = newHours - oldHours;
        const roundedDiff = Math.round(diff * 100) / 100;

        if (roundedDiff === 0) {
            this.env.services.notification.add("No difference in time, no timesheet will be created.", { type: "danger" });
            return;
        }

        let lineData;
        let projectId;

        if (this.state.groupByProject) {
            for (const project of this.state.groupedData) {
                const foundTask = project.tasks.find(t => t.task_id === lineId);
                if (foundTask) {
                    lineData = foundTask;
                    projectId = project.project_id;
                    break;
                }
            }
        } else {
            lineData = this.state.groupedData.find(l => l.task_id === lineId);
            projectId = lineData?.project_id;
        }

        if (!lineData) {
            this.env.services.notification.add("Task not found. Cannot create timesheet.", { type: "danger" });
            return;
        }

        try {
            await this.orm.create("account.analytic.line", [{
                name: "/",
                unit_amount: roundedDiff,
                task_id: lineId,
                project_id: projectId || false,
                date: date,
            }]);
            this.env.services.notification.add("Timesheet created successfully.", { type: "success" });
            await this.fetchTimesheets();
        } catch (error) {
            console.error("Failed to create timesheet:", error);
            this.env.services.notification.add("Error occurred while creating timesheet.", { type: "danger" });
        }
    }

    isOver24Hours(timeStr) {
        if (!timeStr) return false;
        const parts = timeStr.split(':');
        if (parts.length !== 2) return false;
        const h = parseInt(parts[0], 10);
        const m = parseInt(parts[1], 10);
        if (isNaN(h) || isNaN(m)) return false;
        return h > 24 || (h === 24 && m > 0);
    }

    async openAddTimesheetWizardBase() {

        const view_id = await this.orm.searchRead(
                "ir.ui.view",
                [
                    ["name", "=", 'account.analytic.line.form'],
                    ["arch_fs", "=", 'hr_timesheet/views/hr_timesheet_views.xml'],
                    ["priority", "=", 1],
                ],
                ["id"]
            );

        const refDate = new Date(this.state.referenceDate);

        const year = refDate.getFullYear();
        const month = String(refDate.getMonth() + 1).padStart(2, '0');
        const day = String(refDate.getDate()).padStart(2, '0');
        const formattedDateStr = `${year}-${month}-${day}`;

        this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Add Timesheet',
                res_model: 'account.analytic.line',
                view_mode: 'form',
                views: [[view_id[0]['id'], 'form']],
                target: 'new',
                context: {
                    default_date: formattedDateStr,
                },
            });
    }

    onTaskChange(ev) {
        this.state.wizardData.task_id = parseInt(ev.target.value);
    }

    onNameChange(ev) {
        this.state.wizardData.name = ev.target.value;
    }

    onDateChange(ev) {
        this.state.wizardData.date = ev.target.value;
    }

    onHoursInputChange(ev) {
        let input = ev.target.value.trim();
        let hours = 0, minutes = 0;

        if (input.includes(":")) {
            const [hStr, mStr] = input.split(":");
            hours = parseInt(hStr || "0", 10);
            minutes = parseInt(mStr || "0", 10);
        } else if (!isNaN(parseFloat(input))) {
            let floatVal = parseFloat(input);
            hours = Math.floor(floatVal);
            minutes = Math.round((floatVal - hours) * 60);
        } else {
            this.state.wizardData.unit_amount = "00:00";
            return;
        }

        hours += Math.floor(minutes / 60);
        minutes = minutes % 60;

        const formatted = `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;

        this.state.wizardData.unit_amount = formatted;
    }

    addTimesheetFromWizard() {
        const { project_id, task_id, name, date, unit_amount } = this.state.wizardData;
        if (!project_id) {
            this.env.services.notification.add("Please select a Project.", { type: "warning" });
            return;
        }
        if (!task_id) {
            this.env.services.notification.add("Please select a Task.", { type: "warning" });
            return;
        }
        if (!date) {
            this.env.services.notification.add("Please select a Date.", { type: "warning" });
            return;
        }
        if (!unit_amount) {
            this.env.services.notification.add("Please enter Time Spent.", { type: "warning" });
            return;
        }

        const timeParts = unit_amount.split(":");
        if (timeParts.length !== 2 || isNaN(timeParts[0]) || isNaN(timeParts[1])) {
            this.env.services.notification.add("Please enter hours in HH:MM format.", { type: "warning" });
            return;
        }

        const hours = parseInt(timeParts[0], 10);
        const minutes = parseInt(timeParts[1], 10);
        const u_amount = hours + (minutes / 60);

        if (hours < 0 || minutes < 0 || minutes >= 60 || u_amount == 0) {
            this.env.services.notification.add("Give valid time spent.", { type: "warning" });
            return;
        }

        this.orm.create("account.analytic.line", [{
            project_id,
            task_id,
            name : name.trim(),
            date,
            unit_amount : u_amount,
        }]).then(() => {
            this.env.services.notification.add("Timesheet added successfully.", { type: "success" });
            this.closeAddTimesheetWizard();
            this.fetchTimesheets();
        }).catch(error => {
            console.error("Failed to add timesheet:", error);
            this.env.services.notification.add("Error occurred while adding timesheet.", { type: "danger" });

        });
    }

    async goPrevious() {
        const ref = this.state.referenceDate;
        let newDate;
        if (this.state.scale === 'day') {
            newDate = new Date(ref.getFullYear(), ref.getMonth(), ref.getDate() - 1);
        } else if (this.state.scale === 'week') {
            newDate = new Date(ref.getFullYear(), ref.getMonth(), ref.getDate() - 7);
        } else if (this.state.scale === 'month') {
            newDate = new Date(ref.getFullYear(), ref.getMonth() - 1, 1);
        }
        await this.handleReferenceDateChange(newDate);
    }

    async goNext() {
        const ref = this.state.referenceDate;
        let newDate;
        if (this.state.scale === 'day') {
            newDate = new Date(ref.getFullYear(), ref.getMonth(), ref.getDate() + 1);
        } else if (this.state.scale === 'week') {
            newDate = new Date(ref.getFullYear(), ref.getMonth(), ref.getDate() + 7);
        } else if (this.state.scale === 'month') {
            newDate = new Date(ref.getFullYear(), ref.getMonth() + 1, 1);
        }
        await this.handleReferenceDateChange(newDate);
    }

    getDateColumns() {
        const refDate = this.state.referenceDate;
        let dates = [];

        if (this.state.scale === 'day') {
            dates = [refDate];
        } else if (this.state.scale === 'week') {
            const day = refDate.getDay();
            const sunday = new Date(refDate.getFullYear(), refDate.getMonth(), refDate.getDate() - day);
            for (let i = 0; i < 7; i++) {
                dates.push(new Date(sunday.getFullYear(), sunday.getMonth(), sunday.getDate() + i));
            }
        } else if (this.state.scale === 'month') {
            const year = refDate.getFullYear();
            const month = refDate.getMonth();
            const daysInMonth = new Date(year, month + 1, 0).getDate();
            for (let i = 1; i <= daysInMonth; i++) {
                dates.push(new Date(year, month, i));
            }
        }

        this.state.dateColumns = dates;
    }

    async fetchTimesheets() {
        const dateStart = this.formatDateLocal(this.state.dateColumns[0]);
        const dateEnd = this.formatDateLocal(this.state.dateColumns[this.state.dateColumns.length - 1]);

        let timesheetDomain = [
            ["date", ">=", dateStart],
            ["date", "<=", dateEnd],
            ["task_id", "!=", false],
        ];

        if (this.state.user.isAdmin && this.state.selectedEmployeeUserId) {
            timesheetDomain.push(["user_id", "=", parseInt(this.state.selectedEmployeeUserId)]);
        } else if (!this.state.user.isAdmin) {
            timesheetDomain.push(["user_id", "=", this.state.user.userId]);
        }

        const groupedTimesheets = await this.orm.call("account.analytic.line", "read_group", [
            timesheetDomain,
            ["unit_amount:sum"],
            ["task_id"],
        ]);


        const validTaskIds = groupedTimesheets
            .filter(g => g.task_id)
            .map(g => g.task_id[0]);

        if (validTaskIds.length === 0) {
            this.state.groupedData = [];
            return;
        }

        let taskDomain = [
            ["id", "in", validTaskIds],
            ["project_id", "!=", false],
        ];

        if (this.state.user.isAdmin && this.state.selectedEmployeeUserId) {
            taskDomain.push(["user_ids", "in", [parseInt(this.state.selectedEmployeeUserId)]]);
        } else if (!this.state.user.isAdmin) {
            taskDomain.push(["user_ids", "in", [this.state.user.userId]]);
        }

        const tasks = await this.orm.searchRead("project.task", taskDomain, ["id", "name", "project_id"]);

        let detailDomain = [
            ["task_id", "in", validTaskIds],
            ["date", ">=", dateStart],
            ["date", "<=", dateEnd]
        ];

        if (this.state.user.isAdmin && this.state.selectedEmployeeUserId) {
            detailDomain.push(["user_id", "=", parseInt(this.state.selectedEmployeeUserId)]);
        } else if (!this.state.user.isAdmin) {
            detailDomain.push(["user_id", "=", this.state.user.userId]);
        }

        const timesheets = await this.orm.searchRead(
            "account.analytic.line",
            detailDomain,
            ["task_id", "date", "unit_amount"]
        );

        const grouped = tasks.map(task => {
            const times = {};
            this.state.dateColumns.forEach(date => {
                const dateStr = this.formatDateLocal(date);
                const entries = timesheets.filter(t => t.task_id[0] === task.id && t.date === dateStr);
                times[dateStr] = entries.reduce((sum, e) => sum + e.unit_amount, 0);
            });

            return {
                task_id: task.id,
                task_name: task.name,
                project_name: task.project_id ? task.project_id[1] : 'N/A',
                project_id: task.project_id ? task.project_id[0] : false,
                timesheets: times,
            };
        });

        if (this.state.groupByProject) {
            const projectsMap = {};

            grouped.forEach(task => {
                const projectId = task.project_id || 'no_project';
                if (!projectsMap[projectId]) {
                    projectsMap[projectId] = {
                        project_id: task.project_id,
                        project_name: task.project_name,
                        tasks: [],
                        total: 0
                    };
                }
                projectsMap[projectId].tasks.push(task);
                projectsMap[projectId].total += Object.values(task.timesheets).reduce((a, b) => a + b, 0);
            });
            this.state.originalGroupedData = Object.values(projectsMap);
        } else {
            this.state.originalGroupedData = grouped;
        }
        this.state.groupedData = [...this.state.originalGroupedData];
        if (this.state.searchTerm) {
            this.applySearchFilter();
        }
    }

    async onScaleChange(ev) {
        this.state.scale = ev.target.value;
        sessionStorage.setItem('scale', this.state.scale);
        this.getDateColumns();
        await this.fetchTimesheets();
    }

    openProject(projectId) {
        this.actionService.doAction({
            name: "Project",
            type: 'ir.actions.act_window',
            res_model: 'project.project',
            res_id: projectId,
            view_mode: 'form',
            target: 'current',
            views: [[false, "form"]],
        });
    }

    openTask(taskid) {
        this.actionService.doAction({
            name: "Task",
            type: 'ir.actions.act_window',
            res_model: 'project.task',
            res_id: taskid,
            view_mode: 'form',
            target: 'current',
            views: [[false, "form"]],
        });
    }

}

GridRenderer.template = "sttl_grid_timesheet.GridRenderer";
GridRenderer.components = {
    View,
    Field,
    Record,
    ViewScaleSelector,
};
